"""Ficha del camión: los datos del Registro y el código solo los ve y maneja el admin."""

from app.models import Profile

DETAILS = {
    "code": "M02",
    "brand": "Freightliner",
    "model": "Century 112 ST",
    "year": 2004,
    "vin": "1FUBA9CV34LM51521",
    "color": "Rojo",
    "body_type": "Cabezal",
    "traction": "4X2",
}


def test_admin_saves_and_sees_registry_details(api):
    client = api.as_user(api.fleet.admin_id).client
    created = client.post("/trucks", json={"plate": "C 177685", **DETAILS})
    assert created.status_code == 201, created.text
    assert {k: created.json()[k] for k in DETAILS} == DETAILS

    edited = client.patch(f"/trucks/{created.json()['id']}", json={"color": "Blanco"})
    assert edited.status_code == 200
    assert edited.json()["color"] == "Blanco" and edited.json()["vin"] == DETAILS["vin"]


def test_details_hidden_from_dispatcher_and_drivers(api):
    truck_id = api.as_user(api.fleet.admin_id).client.post("/trucks", json={"plate": "C 165166", **DETAILS}).json()["id"]
    api.db.get(Profile, api.fleet.admin_id).role = "dispatcher"
    api.db.flush()
    for user in (api.fleet.admin_id, api.fleet.driver_user_id):
        truck = api.as_user(user).client.get(f"/trucks/{truck_id}").json()
        assert truck["plate"] == "C 165166"
        assert all(truck[k] is None for k in DETAILS)
    # Despacho crea con placa; lo demás se ignora.
    created = api.as_user(api.fleet.admin_id).client.post("/trucks", json={"plate": "C 999999", "vin": "X"})
    assert created.status_code == 201 and created.json()["vin"] is None
