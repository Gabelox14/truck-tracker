from app.models import IntakeFile, Trip, TripCar
from tests.helpers import make_extraction, make_jpeg, make_ogg


def test_review_queue_is_staff_only_and_lists_everything_pending(api):
    api.extractor.readings = [make_extraction(vin_text="1HGCM82633A004353", vin_bbox=None)]
    api.photo()  # carro en revisión (dígito verificador)
    api.audio()  # viaje en revisión (monto dictado por el chofer)
    api.photo(data=make_jpeg(color=(1, 2, 3)), trip=False)  # borrador

    assert api.client.get("/intake/review-queue").status_code == 403
    queue = api.as_user(api.fleet.admin_id).client.get("/intake/review-queue").json()
    assert [trip["id"] for trip in queue["trips"]] == [str(api.fleet.trip.id)]
    assert len(queue["cars"]) == 1 and queue["cars"][0]["review_status"] == "needs_review"
    assert len(queue["drafts"]) == 1 and queue["drafts"][0]["kind"] == "vin_photo"


def test_trip_files_are_listed_for_whoever_can_see_the_trip(api):
    api.photo()
    api.audio()
    files = api.client.get("/intake/files", params={"trip_id": str(api.fleet.trip.id)}).json()
    assert sorted(f["kind"] for f in files) == ["audio", "vin_photo"]
    audio = next(f for f in files if f["kind"] == "audio")
    assert audio["transcript"].startswith("Salí del Coyol")
    assert audio["extraction"]["cost_amount"] == 50000
    other = api.as_user(api.fleet.other_user_id).client.get("/intake/files", params={"trip_id": str(api.fleet.trip.id)})
    assert other.status_code == 403


def test_staff_attaches_a_draft_photo_to_a_trip(api):
    draft_id = api.photo(trip=False).json()["intake_file_id"]
    api.as_user(api.fleet.admin_id)
    response = api.client.post(f"/intake/files/{draft_id}/attach", json={"trip_id": str(api.fleet.trip.id)})
    assert response.status_code == 200
    assert api.db.query(TripCar).filter(TripCar.trip_id == api.fleet.trip.id).count() == 1
    again = api.client.post(f"/intake/files/{draft_id}/attach", json={"trip_id": str(api.fleet.trip.id)})
    assert again.status_code == 409


def test_staff_creates_a_trip_from_a_note_and_a_photo(api):
    audio_id = api.audio(trip=False).json()["intake_file_id"]
    photo_id = api.photo(trip=False).json()["intake_file_id"]
    api.as_user(api.fleet.admin_id)
    payload = {
        "file_ids": [photo_id, audio_id],
        "driver_id": str(api.fleet.driver.id),
        "truck_id": str(api.fleet.truck.id),
        "origin_zone_id": str(api.fleet.origin.id),
        "destination_zone_id": str(api.fleet.destination.id),
        "trip_type": "directo",
        "trip_date": "2026-10-30",
    }
    response = api.client.post("/intake/drafts/create-trip", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["intake_source"] == "upload"
    assert body["status"] == "completed"
    assert body["started_at"].startswith("2026-10-30")
    # El audio llenó el monto y el texto de origen; la foto se cruzó con lo dicho.
    assert (body["amount"], body["currency"]) == (50000, "CRC")
    assert body["origin_text"] == "el Coyol"
    trip = api.db.get(Trip, body["id"])
    car = api.db.query(TripCar).filter(TripCar.trip_id == trip.id).one()
    assert "nota de voz" in car.review_notes
    assert all(api.db.get(IntakeFile, file_id).trip_id == trip.id for file_id in (audio_id, photo_id))


def test_create_trip_validates_zones_and_files(api):
    photo_id = api.photo(trip=False).json()["intake_file_id"]
    api.as_user(api.fleet.admin_id)
    base = {
        "file_ids": [photo_id],
        "driver_id": str(api.fleet.driver.id),
        "truck_id": str(api.fleet.truck.id),
        "origin_zone_id": str(api.fleet.origin.id),
        "destination_zone_id": str(api.fleet.origin.id),
    }
    assert api.client.post("/intake/drafts/create-trip", json=base).status_code == 409
    attached_id = api.as_user(api.fleet.driver_user_id).photo(data=make_jpeg(color=(9, 9, 9))).json()["intake_file_id"]
    api.as_user(api.fleet.admin_id)
    with_attached = {**base, "destination_zone_id": str(api.fleet.destination.id), "file_ids": [attached_id]}
    assert api.client.post("/intake/drafts/create-trip", json=with_attached).status_code == 409


def test_discarding_a_draft_removes_the_file(api):
    body = api.audio(data=make_ogg("descartar"), trip=False).json()
    record = api.db.get(IntakeFile, body["intake_file_id"])
    path = record.storage_path
    assert path in api.storage.objects
    assert api.client.delete(f"/intake/files/{record.id}").status_code == 403

    api.as_user(api.fleet.admin_id)
    assert api.client.delete(f"/intake/files/{record.id}").status_code == 204
    assert path not in api.storage.objects
    assert api.db.get(IntakeFile, body["intake_file_id"]) is None

    attached = api.as_user(api.fleet.driver_user_id).photo().json()["intake_file_id"]
    assert api.as_user(api.fleet.admin_id).client.delete(f"/intake/files/{attached}").status_code == 409


def test_dashboard_never_mixes_currencies(api):
    api.as_user(api.fleet.admin_id)
    trip = api.fleet.trip
    api.client.patch(f"/trips/{trip.id}/amount", json={"amount": 200, "currency": "USD"})
    second = Trip(
        driver_id=api.fleet.driver.id,
        truck_id=api.fleet.truck.id,
        origin_zone_id=api.fleet.origin.id,
        destination_zone_id=api.fleet.destination.id,
        amount=85000,
        currency="CRC",
    )
    api.db.add(second)
    api.db.flush()

    crc = api.client.get("/trips/stats/summary").json()
    assert crc["currency"] == "CRC"
    assert crc["total_amount"] == 85000
    assert crc["trip_count"] == 2
    assert crc["totals_by_currency"] == {"USD": 200, "CRC": 85000}
    usd = api.client.get("/trips/stats/summary", params={"currency": "USD"}).json()
    assert usd["total_amount"] == 200
    assert usd["top_truck"]["total"] == 200
