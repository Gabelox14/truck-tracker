"""Cuentas de chofer que crea el admin: el admin da el nombre y el sistema pone el
usuario y la contraseña. Supabase Auth va simulado: crea y borra filas de auth.users
en la base desechable."""

import json
import re
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.models import Driver, Profile, Trip
from app.services import driver_account_service as accounts
from app.services.auth_admin_service import BAN_FOREVER, AuthAdminError, AuthUserExists, SupabaseAuthAdmin

PASSWORD = re.compile(r"[a-z]{6}-\d{4}")


class FakeAuthAdmin:
    def __init__(self, db):
        self.db = db
        self.users: dict[str, dict] = {}
        self.foreign_emails: set[str] = set()  # cuentas que existen en Supabase pero no en la base

    def create_user(self, email, password, full_name):
        if email in self.foreign_emails or any(u["email"] == email for u in self.users.values()):
            raise AuthUserExists("Ese usuario ya existe")
        user_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"), {"id": user_id, "email": email})
        self.users[user_id] = {"email": email, "password": password, "full_name": full_name, "banned": False}
        return user_id

    def update_user(self, user_id, *, password):
        self.users[user_id]["password"] = password

    def set_banned(self, user_id, *, banned):
        self.users[user_id]["banned"] = banned

    def delete_user(self, user_id):
        self.users.pop(user_id, None)
        self.db.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": user_id})


@pytest.fixture
def auth(api):
    from app.api import drivers as drivers_api
    from app.main import app

    fake = FakeAuthAdmin(api.db)
    app.dependency_overrides[drivers_api.get_auth_admin] = lambda: fake
    return fake


def new_truck(api, code=None):
    from app.models import Truck

    truck = Truck(plate=f"T-{uuid.uuid4().hex[:6]}", code=code)
    api.db.add(truck)
    api.db.flush()
    return truck


def create(api, full_name="Carlos", truck=None, driver_type="fijo", **payload):
    body = {
        "full_name": full_name,
        "truck_id": str((truck or new_truck(api)).id),
        "driver_type": driver_type,
        **payload,
    }
    return api.as_user(api.fleet.admin_id).client.post("/drivers/accounts", json=body)


def user_of(auth, username):
    return next(u for u in auth.users.values() if u["email"] == accounts.email_for(username))


# --- sin base de datos -------------------------------------------------------


def test_generated_password_is_easy_to_type():
    assert PASSWORD.fullmatch(accounts.generate_password())
    assert len({accounts.generate_password() for _ in range(20)}) > 15


def test_username_comes_from_the_name():
    assert accounts.username_candidates("  Carlos Pérez ")[:3] == ["carlos", "carlos.perez", "carlos2"]
    assert accounts.username_candidates("JOHNNY")[:2] == ["johnny", "johnny2"]
    assert accounts.username_candidates("Martín")[0] == "martin"
    with pytest.raises(accounts.DriverAccountError):
        accounts.username_candidates("¿?")


def test_username_only_for_admin_created_accounts():
    assert accounts.username_for(accounts.email_for("nelson")) == "nelson"
    assert accounts.username_for("alguien@gmail.com") is None
    assert accounts.username_for(None) is None


def test_supabase_admin_requests_and_errors():
    seen = []

    def handler(request: httpx.Request):
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, request.url.path, body))
        if request.method == "POST" and body["email"] == "dup@x":
            return httpx.Response(422, json={"error_code": "email_exists", "msg": "already been registered"})
        if request.method == "DELETE":
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json={"id": "u-1"})

    admin = SupabaseAuthAdmin("http://sb.test", "key", httpx.Client(transport=httpx.MockTransport(handler)))
    assert admin.create_user("carlos@x", "bodemi-4821", "Carlos") == "u-1"
    assert seen[0] == (
        "POST",
        "/auth/v1/admin/users",
        {"email": "carlos@x", "password": "bodemi-4821", "email_confirm": True, "user_metadata": {"full_name": "Carlos"}},
    )
    admin.update_user("u-1", password="nueva-1234")
    admin.set_banned("u-1", banned=True)
    admin.set_banned("u-1", banned=False)
    assert [s[2] for s in seen[1:]] == [{"password": "nueva-1234"}, {"ban_duration": BAN_FOREVER}, {"ban_duration": "none"}]
    assert all(s[1] == "/auth/v1/admin/users/u-1" and s[0] == "PUT" for s in seen[1:])
    with pytest.raises(AuthUserExists):
        admin.create_user("dup@x", "x" * 8, "Dup")
    with pytest.raises(AuthAdminError):
        admin.delete_user("u-1")


# --- con base de datos -------------------------------------------------------


def test_admin_gives_the_name_and_the_system_gives_credentials(api, auth):
    response = create(api, "Carlos Pérez", cedula="1-1111-1111")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == "carlos"
    assert PASSWORD.fullmatch(body["password"])
    assert body["driver"]["active"] is True and body["driver"]["username"] == "carlos"

    (user_id, user), = auth.users.items()
    assert user["email"] == accounts.email_for("carlos") and user["password"] == body["password"]
    profile = api.db.get(Profile, user_id)
    assert (profile.role, profile.full_name, profile.cedula) == ("driver", "Carlos Pérez", "1-1111-1111")

    # Al entrar por primera vez ya está asignado: no pasa por "pendiente".
    me = api.as_user(user_id).client.post("/profiles/me")
    assert me.status_code == 200, me.text
    assert me.json()["is_assigned"] is True


def test_repeated_names_get_their_own_username(api, auth):
    assert create(api, "Juan").json()["username"] == "juan"
    assert create(api, "Juan Mora").json()["username"] == "juan.mora"
    assert create(api, "Juan").json()["username"] == "juan2"
    # Una cuenta que Supabase tiene pero la base no: se salta.
    auth.foreign_emails.add(accounts.email_for("nelson"))
    assert create(api, "Nelson").json()["username"] == "nelson2"
    assert api.db.query(Profile).filter(Profile.cedula.is_(None)).count() == 4


def test_only_admin_manages_accounts(api, auth):
    api.db.get(Profile, api.fleet.admin_id).role = "dispatcher"
    api.db.flush()
    assert create(api).status_code == 403
    assert auth.users == {}


def test_list_shows_username_only_for_managed_accounts(api, auth):
    create(api)
    drivers = api.as_user(api.fleet.admin_id).client.get("/drivers").json()
    by_name = {d["full_name"]: d for d in drivers}
    assert by_name["Carlos"]["username"] == "carlos"
    assert by_name["Chofer Uno"]["username"] is None and by_name["Chofer Uno"]["email"] == "chofer@test"


def test_reset_password_gives_a_new_one(api, auth):
    created = create(api).json()
    client = api.as_user(api.fleet.admin_id).client
    reset = client.post(f"/drivers/{created['driver']['id']}/password")
    assert reset.status_code == 200, reset.text
    assert reset.json()["username"] == "carlos"
    assert PASSWORD.fullmatch(reset.json()["password"]) and reset.json()["password"] != created["password"]
    assert user_of(auth, "carlos")["password"] == reset.json()["password"]

    # Un chofer que se registró solo maneja su propia contraseña.
    assert client.post(f"/drivers/{api.fleet.driver.id}/password").status_code == 422


def test_deactivate_blocks_login_and_reactivate_restores_it(api, auth):
    driver_id = create(api).json()["driver"]["id"]
    client = api.as_user(api.fleet.admin_id).client

    off = client.patch(f"/drivers/{driver_id}", json={"active": False})
    assert off.status_code == 200 and off.json()["active"] is False
    assert user_of(auth, "carlos")["banned"] is True

    on = client.patch(f"/drivers/{driver_id}", json={"active": True})
    assert on.status_code == 200 and on.json()["active"] is True
    assert user_of(auth, "carlos")["banned"] is False

    # Los que se registraron solos se desactivan como antes, sin tocar Supabase.
    assert client.patch(f"/drivers/{api.fleet.driver.id}", json={"active": False}).json()["active"] is False


def test_delete_account_removes_access(api, auth):
    driver_id = create(api).json()["driver"]["id"]
    user_id = next(iter(auth.users))
    response = api.as_user(api.fleet.admin_id).client.delete(f"/drivers/{driver_id}")
    assert response.status_code == 204, response.text
    assert auth.users == {}
    api.db.expire_all()
    assert api.db.get(Profile, user_id) is None
    assert api.db.get(Driver, driver_id) is None


def test_delete_with_trips_is_refused(api, auth):
    driver_id = create(api).json()["driver"]["id"]
    fleet = api.fleet
    api.db.add(Trip(driver_id=driver_id, truck_id=fleet.truck.id, origin_zone_id=fleet.origin.id, destination_zone_id=fleet.destination.id))
    api.db.flush()
    assert api.as_user(fleet.admin_id).client.delete(f"/drivers/{driver_id}").status_code == 409
    assert len(auth.users) == 1


def test_truck_and_type_are_required(api, auth):
    client = api.as_user(api.fleet.admin_id).client
    truck = new_truck(api)
    assert client.post("/drivers/accounts", json={"full_name": "Sin Camion", "driver_type": "fijo"}).status_code == 422
    bad_type = create(api, truck=truck, driver_type="jefe")
    assert bad_type.status_code == 422 and "tipo" in bad_type.json()["detail"]
    missing = client.post(
        "/drivers/accounts", json={"full_name": "X", "truck_id": str(uuid.uuid4()), "driver_type": "fijo"}
    )
    assert missing.status_code == 422
    assert auth.users == {}  # no se crea la cuenta si la asignación no sirve


def test_one_active_driver_per_truck(api, auth):
    truck = new_truck(api, code="M01")
    carlos = create(api, "Carlos", truck=truck).json()["driver"]
    taken = create(api, "Martin", truck=truck)
    assert taken.status_code == 409
    assert "M01" in taken.json()["detail"] and "Carlos" in taken.json()["detail"]
    assert len(auth.users) == 1

    client = api.as_user(api.fleet.admin_id).client
    other = create(api, "Martin", driver_type="suplente").json()["driver"]
    # Pasarle el camión a otro chofer activo: no, hasta desactivar al que lo tiene.
    assert client.patch(f"/drivers/{other['id']}", json={"truck_id": str(truck.id)}).status_code == 409
    assert client.patch(f"/drivers/{carlos['id']}", json={"active": False}).status_code == 200
    moved = client.patch(f"/drivers/{other['id']}", json={"truck_id": str(truck.id)})
    assert moved.status_code == 200 and moved.json()["truck_id"] == str(truck.id)

    # Carlos no puede volver con un camión ocupado; sí con uno libre.
    assert client.patch(f"/drivers/{carlos['id']}", json={"active": True}).status_code == 409
    free = new_truck(api)
    back = client.patch(f"/drivers/{carlos['id']}", json={"active": True, "truck_id": str(free.id)})
    assert back.status_code == 200, back.text
    assert user_of(auth, "carlos")["banned"] is False


def test_driver_type_only_for_admin(api, auth):
    driver = create(api, driver_type="tercero").json()["driver"]
    assert driver["driver_type"] == "tercero"
    api.db.get(Profile, api.fleet.admin_id).role = "dispatcher"
    api.db.flush()
    client = api.as_user(api.fleet.admin_id).client
    listed = {d["id"]: d for d in client.get("/drivers").json()}
    assert listed[driver["id"]]["driver_type"] is None and listed[driver["id"]]["truck_id"] == driver["truck_id"]
    assert client.patch(f"/drivers/{driver['id']}", json={"driver_type": "fijo"}).status_code == 403
    # Despacho sí puede desactivarlo.
    assert client.patch(f"/drivers/{driver['id']}", json={"active": False}).status_code == 200


def test_driver_trips_use_the_assigned_truck(api, auth):
    truck = new_truck(api)
    created = create(api, truck=truck).json()
    user_id = next(iter(auth.users))
    me = api.as_user(user_id).client.post("/profiles/me").json()
    assert (me["truck_id"], me["truck_plate"]) == (str(truck.id), truck.plate)

    fleet = api.fleet
    trip = api.as_user(user_id).client.post(
        "/trips",
        json={
            "truck_id": str(fleet.truck.id),  # se ignora: sale en su camión
            "origin_zone_id": str(fleet.origin.id),
            "destination_zone_id": str(fleet.destination.id),
        },
    )
    assert trip.status_code == 201, trip.text
    assert trip.json()["truck_id"] == str(truck.id) == created["driver"]["truck_id"]


def test_existing_profile_loads_without_signup_metadata(api):
    # Antes /profiles/me exigía cédula en los metadatos aunque el perfil existiera.
    assert api.as_user(api.fleet.driver_user_id).client.post("/profiles/me").status_code == 200
