import pytest
from fastapi.testclient import TestClient

from app.api import intake as intake_api
from app.api.deps import require_staff_or_driver
from app.main import app
from app.models import IntakeFile, TripCar
from tests.helpers import FailingExtractor, FakeExtractor, FakeStorage, make_extraction, make_jpeg, post_photo


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


# --- Validaciones que no necesitan base de datos -----------------------------


@pytest.fixture
def bare_client():
    app.dependency_overrides[require_staff_or_driver] = lambda: "00000000-0000-0000-0000-000000000001"
    app.dependency_overrides[intake_api.get_extractor] = lambda: FakeExtractor(make_extraction())
    app.dependency_overrides[intake_api.get_storage] = FakeStorage
    return TestClient(app)


def test_requires_authentication():
    assert post_photo(TestClient(app), make_jpeg()).status_code in (401, 403)


def test_without_api_key_answers_503():
    app.dependency_overrides[require_staff_or_driver] = lambda: "00000000-0000-0000-0000-000000000001"
    response = post_photo(TestClient(app), make_jpeg())
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_rejects_non_image(bare_client):
    assert post_photo(bare_client, b"%PDF-1.4", "x.pdf", "application/pdf").status_code == 415


def test_rejects_empty_and_oversized_files(bare_client, monkeypatch):
    assert post_photo(bare_client, b"").status_code == 400
    monkeypatch.setattr(intake_api.settings, "intake_max_image_mb", 0.01)
    assert post_photo(bare_client, make_jpeg() + b"0" * 20000).status_code == 413


# --- Flujo completo contra una base desechable (TEST_DATABASE_URL) -----------


def test_photo_on_own_trip_creates_the_car(api):
    response = api.photo()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["duplicate"] is False
    assert body["trip_id"] == str(api.fleet.trip.id)

    car = api.db.get(TripCar, body["trip_car_id"])
    assert car.vin == "1HGCM82633A004352"
    assert car.vin_raw == "1HGCM82633A004352"
    assert car.vin_valid is True and car.check_digit_ok is True
    assert car.brand == "Honda" and car.model == "Accord" and car.model_year == 2003
    assert car.make_from_photo == "Honda" and car.color == "gris"
    assert float(car.ocr_confidence) == 0.95
    assert car.review_status == "ok"
    assert str(car.created_by) == api.fleet.driver_user_id

    record = api.db.get(IntakeFile, body["intake_file_id"])
    assert record.kind == "vin_photo" and record.status == "processed"
    assert record.ai_model == "claude-sonnet-5-5"
    assert (record.input_tokens, record.output_tokens) == (1500, 200)
    assert car.photo_file_id == record.id
    assert record.storage_path in api.storage.objects
    assert record.storage_path.startswith("vin-photos/")


def test_repeated_photo_is_not_reprocessed(api):
    first = api.photo().json()
    second = api.photo().json()
    assert second["duplicate"] is True
    assert second["intake_file_id"] == first["intake_file_id"]
    assert second["trip_car_id"] == first["trip_car_id"]
    assert len(api.extractor.calls) == 1
    assert api.db.query(TripCar).filter(TripCar.trip_id == api.fleet.trip.id).count() == 1


def test_draft_photo_is_attached_when_sent_again_with_trip(api):
    draft = api.photo(trip=False).json()
    assert draft["trip_id"] is None and draft["trip_car_id"] is None
    attached = api.photo().json()
    assert attached["duplicate"] is True
    assert attached["trip_id"] == str(api.fleet.trip.id)
    assert attached["trip_car_id"] is not None
    assert len(api.extractor.calls) == 1


def test_needs_review_reading_is_saved_as_needs_review(api):
    api.extractor = FakeExtractor(make_extraction(vin_text="1HGCM82633A004353", vin_bbox=None))
    body = api.photo().json()
    car = api.db.get(TripCar, body["trip_car_id"])
    assert car.review_status == "needs_review"
    assert "dígito verificador" in car.review_notes
    assert car.check_digit_ok is False


def test_driver_cannot_upload_to_someone_elses_trip(api):
    api.as_user(api.fleet.other_user_id)
    assert api.photo().status_code == 403


def test_claude_failure_is_recorded_and_retry_does_not_reupload(api):
    api.extractor = FailingExtractor()
    response = api.photo()
    assert response.status_code == 502
    record = api.db.query(IntakeFile).one()
    assert record.status == "failed" and "529" in record.error
    uploads_before = dict(api.storage.objects)

    api.extractor = FakeExtractor(make_extraction())
    retry = api.photo()
    assert retry.status_code == 200
    assert retry.json()["intake_file_id"] == str(record.id)
    assert api.db.get(IntakeFile, record.id).status == "processed"
    assert api.storage.objects == uploads_before


def test_signed_url_respects_trip_access(api):
    file_id = api.photo().json()["intake_file_id"]
    owner = api.client.get(f"/intake/files/{file_id}/url")
    assert owner.status_code == 200
    assert owner.json()["expires_in"] == 600
    assert api.as_user(api.fleet.admin_id).client.get(f"/intake/files/{file_id}/url").status_code == 200
    assert api.as_user(api.fleet.other_user_id).client.get(f"/intake/files/{file_id}/url").status_code == 403


def test_staff_corrects_and_confirms_a_car(api):
    car_id = api.photo().json()["trip_car_id"]
    trip_id = api.fleet.trip.id
    assert api.client.patch(f"/trips/{trip_id}/cars/{car_id}", json={"review_status": "confirmed"}).status_code == 403

    api.as_user(api.fleet.admin_id)
    response = api.client.patch(
        f"/trips/{trip_id}/cars/{car_id}", json={"vin": "1m8gdm9axkp042788", "review_status": "confirmed"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["vin"] == "1M8GDM9AXKP042788"
    assert body["check_digit_ok"] is True
    assert body["review_status"] == "confirmed"
    assert body["brand"] == "Honda"


def test_manual_car_with_vin_is_validated(api):
    api.as_user(api.fleet.admin_id)
    response = api.client.post(
        f"/trips/{api.fleet.trip.id}/cars", json={"brand": "Toyota", "vin": "1hgcm82633a004353", "model_year": 2019}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["vin"] == "1HGCM82633A004353"
    assert body["vin_valid"] is True
    assert body["check_digit_ok"] is False
    assert body["photo_file_id"] is None


def test_amount_keeps_or_changes_currency(api):
    api.as_user(api.fleet.admin_id)
    trip_id = api.fleet.trip.id
    usd = api.client.patch(f"/trips/{trip_id}/amount", json={"amount": 150, "currency": "USD"}).json()
    assert (usd["amount"], usd["currency"]) == (150, "USD")
    kept = api.client.patch(f"/trips/{trip_id}/amount", json={"amount": 175}).json()
    assert (kept["amount"], kept["currency"]) == (175, "USD")
    assert api.client.patch(f"/trips/{trip_id}/amount", json={"amount": 10, "currency": "EUR"}).status_code == 422


def test_review_confirms_trip_with_corrections(api):
    trip_id = api.fleet.trip.id
    assert api.client.patch(f"/trips/{trip_id}/review", json={}).status_code == 403

    api.as_user(api.fleet.admin_id)
    body = api.client.patch(f"/trips/{trip_id}/review", json={"amount": 85000, "currency": "CRC"}).json()
    assert body["review_status"] == "confirmed"
    assert (body["amount"], body["currency"]) == (85000, "CRC")

    same_zone = {"destination_zone_id": str(api.fleet.origin.id)}
    assert api.client.patch(f"/trips/{trip_id}/review", json=same_zone).status_code == 422
