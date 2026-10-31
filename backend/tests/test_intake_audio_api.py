from fastapi.testclient import TestClient

from app.api import intake as intake_api
from app.api.deps import require_staff_or_driver
from app.main import app
from app.models import IntakeFile, Trip, TripCar
from app.schemas.intake import VehicleMention
from tests.helpers import FailingExtractor, FailingTranscriber, FakeExtractor, make_extraction, make_ogg, place, post_audio


def test_audio_without_transcription_key_answers_503():
    app.dependency_overrides[require_staff_or_driver] = lambda: "00000000-0000-0000-0000-000000000001"
    app.dependency_overrides[intake_api.get_extractor] = lambda: FakeExtractor(make_extraction())
    try:
        response = post_audio(TestClient(app), make_ogg())
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "TRANSCRIPTION_API_KEY" in response.json()["detail"]


def test_driver_note_fills_the_trip_and_asks_to_confirm_the_amount(api):
    response = api.audio()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transcript"].startswith("Salí del Coyol")
    assert body["origin_zone_id"] == str(api.fleet.origin.id)
    assert (body["cost_amount"], body["cost_currency"]) == (50000, "CRC")
    assert body["trip_review_status"] == "needs_review"
    assert body["trip_review_reasons"] == ["Monto dictado por el chofer: falta confirmarlo"]

    trip = api.db.get(Trip, api.fleet.trip.id)
    assert (float(trip.amount), trip.currency) == (50000, "CRC")
    assert (trip.origin_text, trip.destination_text) == ("el Coyol", "la Uruca")
    assert trip.review_status == "needs_review"

    record = api.db.get(IntakeFile, body["intake_file_id"])
    assert record.kind == "audio" and record.mime_type == "audio/ogg"
    assert record.transcript.startswith("Salí del Coyol")
    assert float(record.duration_seconds) == 42.0
    assert (record.input_tokens, record.output_tokens) == (600, 150)
    assert record.storage_path.startswith("audios/")
    # La transcripción recibió el vocabulario con las zonas de la empresa.
    assert api.fleet.origin.name in api.transcriber.calls[0]["prompt"]
    assert api.fleet.origin.name in api.extractor.trip_calls[0]["zone_names"]


def test_staff_note_that_matches_the_trip_needs_no_review(api):
    api.as_user(api.fleet.admin_id)
    body = api.audio().json()
    assert body["trip_review_status"] == "ok"
    assert body["trip_review_reasons"] == []


def test_note_that_contradicts_the_trip_goes_to_review(api):
    api.as_user(api.fleet.admin_id)
    api.client.patch(f"/trips/{api.fleet.trip.id}/amount", json={"amount": 60000, "currency": "CRC"})
    api.extractor.trip_readings = [
        api.trip_extraction(destination=place("Lindora", "Lindora, Santa Ana", api.fleet.origin.name))
    ]
    reasons = api.audio().json()["trip_review_reasons"]
    assert any("llegó a" in reason and "pero el viaje tiene" in reason for reason in reasons)
    assert "El audio dice ₡50,000.00, pero el viaje tiene ₡60,000.00" in reasons
    # El monto que ya tenía el viaje no se pisa.
    assert float(api.db.get(Trip, api.fleet.trip.id).amount) == 60000


def test_vehicles_in_the_note_are_crossed_with_the_photos(api):
    api.photo()  # Honda Accord por foto
    reasons = api.audio().json()["trip_review_reasons"]
    assert "El audio menciona un Toyota Hilux que no está en las fotos del viaje" in reasons


def test_photo_after_the_note_is_crossed_too(api):
    api.audio()  # menciona una Toyota Hilux
    car = api.db.get(TripCar, api.photo().json()["trip_car_id"])
    assert car.review_status == "needs_review"
    assert "La marca no coincide con lo dicho en la nota de voz (Toyota)" in car.review_notes


def test_photo_matching_the_note_stays_ok(api):
    api.extractor.trip_readings = [
        api.trip_extraction(vehicle_mentions=[VehicleMention(make="Honda", model="Accord", color=None, plate=None)])
    ]
    api.audio()
    car = api.db.get(TripCar, api.photo().json()["trip_car_id"])
    assert car.review_status == "ok"


def test_repeated_note_is_not_transcribed_again(api):
    first = api.audio().json()
    second = api.audio().json()
    assert second["duplicate"] is True
    assert second["intake_file_id"] == first["intake_file_id"]
    assert len(api.transcriber.calls) == 1
    assert len(api.extractor.trip_calls) == 1


def test_draft_note_without_trip_lists_what_is_missing(api):
    api.extractor.trip_readings = [api.trip_extraction(cost_amount=None, cost_currency=None, cost_spoken=None)]
    body = api.audio(trip=False).json()
    assert body["trip_id"] is None
    assert body["review_status"] == "needs_review"
    assert "No se dijo el costo" in body["review_reasons"]
    assert api.db.get(Trip, api.fleet.trip.id).amount is None


def test_failed_extraction_keeps_the_transcript_for_the_retry(api):
    good = api.extractor
    api.extractor = FailingExtractor()
    assert api.audio().status_code == 502
    record = api.db.query(IntakeFile).one()
    assert record.status == "failed" and record.transcript

    api.extractor = good
    assert api.audio().status_code == 200
    assert len(api.transcriber.calls) == 1


def test_transcription_failure_answers_502(api):
    api.transcriber = FailingTranscriber()
    response = api.audio()
    assert response.status_code == 502
    assert "transcripción" in response.json()["detail"]


def test_non_audio_is_rejected(api):
    assert api.audio(data=b"%PDF-1.4 nada").status_code == 415
