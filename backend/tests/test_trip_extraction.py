"""Transcripciones de ejemplo con la respuesta de Claude simulada: se prueba lo
que el backend hace con lo extraído (zonas, moneda, motivos de revisión)."""

import uuid
from types import SimpleNamespace

from app.schemas.intake import TranscriptionOut, VehicleMention
from app.services import audio_intake_service
from app.services.claude_service import ClaudeUsage
from tests.helpers import make_trip_extraction, place

ZONES = [SimpleNamespace(id=uuid.uuid4(), name=name) for name in ("Coyol", "Lindora", "Uruca")]
COYOL, LINDORA, URUCA = ZONES
TRANSCRIPTION = TranscriptionOut(model="whisper-large-v3", duration_seconds=40.0)
USAGE = ClaudeUsage(model="claude-sonnet-5-5", input_tokens=600, output_tokens=150)


def build(transcript, extraction):
    return audio_intake_service.build_audio_result(transcript, TRANSCRIPTION, extraction, USAGE, ZONES)


def test_clear_note_with_rojos_is_ok():
    # "Salí del Coyol a la Uruca con una Hilux blanca, fueron 50 rojos" → Claude: 50000 CRC.
    result = build("Salí del Coyol a la Uruca con una Hilux blanca, fueron 50 rojos", make_trip_extraction())
    assert result.origin_zone_id == COYOL.id
    assert result.destination_zone_id == URUCA.id
    assert (result.cost_amount, result.cost_currency) == (50000, "CRC")
    assert result.currency_assumed is False
    assert result.review_status == "ok"
    assert result.usage.model_dump() == {"model": "claude-sonnet-5-5", "input_tokens": 600, "output_tokens": 150, "calls": 1}


def test_amount_without_currency_assumes_colones_and_asks_review():
    # "De Lindora a la Uruca, ochenta y cinco mil" → número sin moneda.
    extraction = make_trip_extraction(
        origin=place("Lindora", "Lindora, Santa Ana", "Lindora"),
        cost_amount=85000,
        cost_currency=None,
        cost_spoken="ochenta y cinco mil",
    )
    result = build("De Lindora a la Uruca, ochenta y cinco mil", extraction)
    assert (result.cost_amount, result.cost_currency) == (85000, "CRC")
    assert result.currency_assumed is True
    assert result.review_status == "needs_review"
    assert "No se dijo la moneda: se asumió colones" in result.review_reasons


def test_dollars_are_kept():
    extraction = make_trip_extraction(cost_amount=150, cost_currency="USD", cost_spoken="ciento cincuenta dólares")
    result = build("Coyol a Uruca, ciento cincuenta dólares", extraction)
    assert (result.cost_amount, result.cost_currency) == (150, "USD")
    assert result.review_status == "ok"


def test_place_outside_the_zones_is_flagged_but_kept():
    extraction = make_trip_extraction(destination=place("Caldera", "Puerto Caldera, Puntarenas", None))
    result = build("Del Coyol a Caldera, 120 rojos", extraction)
    assert result.destination_zone_id is None
    assert result.extraction.destination.spoken == "Caldera"
    assert any("Puerto Caldera" in reason and "zona registrada" in reason for reason in result.review_reasons)


def test_zone_is_matched_from_what_was_said_when_claude_leaves_it_empty():
    extraction = make_trip_extraction(origin=place("el coyol de Alajuela", "El Coyol, Alajuela", None))
    assert build("...", extraction).origin_zone_id == COYOL.id


def test_missing_data_is_listed_for_drafts():
    extraction = make_trip_extraction(origin=None, destination=None, cost_amount=None, cost_currency=None, cost_spoken=None)
    result = build("Ya llegué, todo bien", extraction)
    assert result.review_reasons == ["No se dijo de dónde salió", "No se dijo a dónde llegó", "No se dijo el costo"]


def test_silence_or_unintelligible_audio():
    result = audio_intake_service.build_audio_result("", TRANSCRIPTION, None, None, ZONES)
    assert result.review_status == "needs_review"
    assert result.review_reasons == ["No se entendió nada en el audio"]
    assert result.usage is None


def test_low_confidence_is_flagged():
    result = build("...", make_trip_extraction(confidence=0.4))
    assert any("poca seguridad" in reason for reason in result.review_reasons)


def test_mention_conflicts_against_photographed_cars():
    cars = [SimpleNamespace(brand="Toyota", make_from_photo="Toyota"), SimpleNamespace(brand=None, make_from_photo="Hyundai")]
    mentions = [
        VehicleMention(make="toyota", model="Hilux", color=None, plate=None),
        VehicleMention(make="Nissan", model="Frontier", color=None, plate=None),
        VehicleMention(make=None, model=None, color="rojo", plate="BKL123"),
    ]
    assert audio_intake_service.mention_conflicts(mentions, cars) == [
        "El audio menciona un Nissan Frontier que no está en las fotos del viaje"
    ]
    assert audio_intake_service.mention_conflicts(mentions, []) == []
