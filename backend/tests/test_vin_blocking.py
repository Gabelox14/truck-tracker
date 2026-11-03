"""Un VIN malo o que no coincide con la marca genera alerta y no deja guardar el
vehículo, confirmarlo, ni completar o confirmar el viaje."""

from app.models import TripCar
from app.services import vin_service

GOOD = "1HGCM82633A004352"  # Honda, dígito verificador correcto
SUZUKI = "MA3FL61SXTA573858"  # VIN real del registro de directos


def test_vin_problem_rules():
    assert vin_service.vin_problem(None) is None
    assert vin_service.vin_problem(GOOD, "Honda") is None
    assert vin_service.vin_problem(SUZUKI, "Suzuki") is None
    assert "18 caracteres" in vin_service.vin_problem("MA3FL61S4VA5933955", "Suzuki")  # error real del Excel
    assert "dígito verificador" in vin_service.vin_problem("1HGCM82633A004353", "Honda")
    assert "no se pudieron leer" in vin_service.vin_problem("1HGCM8263?A004352")
    assert vin_service.vin_problem(SUZUKI, "Toyota") == "El VIN es de un Suzuki, pero el vehículo dice Toyota"
    # Sin marca conocida para ese prefijo no se puede decir que no coincida.
    assert vin_service.vin_problem(GOOD, "Toyota") is None


def admin(api):
    return api.as_user(api.fleet.admin_id).client


def cars_url(api):
    return f"/trips/{api.fleet.trip.id}/cars"


def test_bad_vin_is_not_saved(api):
    response = admin(api).post(cars_url(api), json={"brand": "Honda", "vin": "1HGCM82633A00435"})
    assert response.status_code == 422
    assert "16 caracteres" in response.json()["detail"]
    mismatch = admin(api).post(cars_url(api), json={"brand": "Toyota", "vin": SUZUKI})
    assert mismatch.status_code == 422 and "Suzuki" in mismatch.json()["detail"]
    assert api.db.query(TripCar).filter(TripCar.trip_id == api.fleet.trip.id).count() == 0

    car = admin(api).post(cars_url(api), json={"brand": "Honda", "vin": GOOD})
    assert car.status_code == 201 and car.json()["vin_problem"] is None
    broken = admin(api).patch(f"{cars_url(api)}/{car.json()['id']}", json={"vin": "1HGCM82633A004353"})
    assert broken.status_code == 422
    # Lo que no toca el VIN se puede seguir guardando.
    assert admin(api).patch(f"{cars_url(api)}/{car.json()['id']}", json={"amount": 30000}).status_code == 200


def ocr_car(api, vin, brand):
    """Vehículo leído de una foto: se guarda tal cual para que alguien lo corrija."""
    car = TripCar(trip_id=api.fleet.trip.id, make_from_photo=brand, vin=vin, review_status="needs_review")
    api.db.add(car)
    api.db.flush()
    return car


def test_bad_vin_blocks_completing_and_confirming(api):
    car = ocr_car(api, "MA3FL61S4VA5933955", "Suzuki")
    listed = api.as_user(api.fleet.driver_user_id).client.get(cars_url(api)).json()
    assert "18 caracteres" in listed[0]["vin_problem"]  # la alerta llega a la pantalla

    complete = api.as_user(api.fleet.driver_user_id).client.post(f"/trips/{api.fleet.trip.id}/complete")
    assert complete.status_code == 409
    assert "corrige primero el VIN" in complete.json()["detail"] and "MA3FL61S4VA5933955" in complete.json()["detail"]
    assert admin(api).patch(f"/trips/{api.fleet.trip.id}/review", json={}).status_code == 409
    assert admin(api).patch(f"{cars_url(api)}/{car.id}", json={"review_status": "confirmed"}).status_code == 422

    # Corregido el VIN, ya se puede.
    fixed = admin(api).patch(f"{cars_url(api)}/{car.id}", json={"vin": SUZUKI, "brand": "Suzuki"})
    assert fixed.status_code == 200 and fixed.json()["vin_problem"] is None
    assert api.as_user(api.fleet.driver_user_id).client.post(f"/trips/{api.fleet.trip.id}/complete").status_code == 200


def test_fe_rows_show_the_problem(api):
    ocr_car(api, SUZUKI, "Toyota")
    rows = admin(api).get("/trips/export/fe/preview").json()
    row = next(r for r in rows if r["vin"] == SUZUKI)
    assert row["vin_problem"] == row["vin_status"] == "El VIN es de un Suzuki, pero el vehículo dice Toyota"
