import hashlib
import re
import unicodedata
from datetime import date

from sqlalchemy.orm import Session

from app.core.time import costa_rica_today
from app.models.intake_file import IntakeFile
from app.models.trip import Trip
from app.models.trip_car import TripCar
from app.models.zone import Zone
from app.repositories import intake_file_repository, trip_car_repository, zone_repository
from app.schemas.intake import (
    AiUsageOut,
    AudioIntakeOut,
    PlaceExtraction,
    TranscriptionOut,
    TripAudioExtraction,
    TripAudioResult,
    VehicleMention,
)
from app.services import audio_service, vin_service
from app.services.claude_service import ClaudeExtractionError, ClaudeExtractor, ClaudeUsage
from app.services.storage_service import SupabaseStorage, object_path
from app.services.transcription_service import Transcriber, TranscriptionError, build_prompt

CONFIDENCE_THRESHOLD = 0.7


def _fold(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_accents.lower()).split())


def match_zone(place: PlaceExtraction | None, zones: list[Zone]) -> Zone | None:
    """La zona que propuso Claude si existe; si no, una zona cuyo nombre aparezca
    como palabra completa en lo que se dijo ("el Coyol de Alajuela" → Coyol)."""
    if place is None:
        return None
    by_name = {_fold(zone.name): zone for zone in zones}
    if place.zone and _fold(place.zone) in by_name:
        return by_name[_fold(place.zone)]
    for text in (place.normalized, place.spoken):
        padded = f" {_fold(text)} "
        for key, zone in by_name.items():
            if key and f" {key} " in padded:
                return zone
    return None


def format_money(amount: float, currency: str) -> str:
    symbol = "$" if currency == "USD" else "₡"
    return f"{symbol}{amount:,.2f}"


def build_audio_result(
    transcript: str,
    transcription: TranscriptionOut,
    extraction: TripAudioExtraction | None,
    usage: ClaudeUsage | None,
    zones: list[Zone],
) -> TripAudioResult:
    """Resultado como borrador: los motivos de revisión piden lo que falta para crear el viaje."""
    reasons: list[str] = []
    origin_zone = destination_zone = None
    amount = currency = None
    currency_assumed = False

    if extraction is None:
        reasons.append("No se entendió nada en el audio")
    else:
        origin_zone = match_zone(extraction.origin, zones)
        destination_zone = match_zone(extraction.destination, zones)
        if extraction.origin is None:
            reasons.append("No se dijo de dónde salió")
        elif origin_zone is None:
            reasons.append(f"El origen «{extraction.origin.normalized}» no es una zona registrada")
        if extraction.destination is None:
            reasons.append("No se dijo a dónde llegó")
        elif destination_zone is None:
            reasons.append(f"El destino «{extraction.destination.normalized}» no es una zona registrada")

        amount, currency = extraction.cost_amount, extraction.cost_currency
        if amount is None:
            reasons.append("No se dijo el costo")
        elif currency is None:
            currency, currency_assumed = "CRC", True
            reasons.append("No se dijo la moneda: se asumió colones")
        if extraction.confidence < CONFIDENCE_THRESHOLD:
            reasons.append(f"Extracción con poca seguridad ({extraction.confidence:.0%})")

    return TripAudioResult(
        transcript=transcript,
        extraction=extraction,
        origin_zone_id=origin_zone.id if origin_zone else None,
        destination_zone_id=destination_zone.id if destination_zone else None,
        cost_amount=amount,
        cost_currency=currency,
        currency_assumed=currency_assumed,
        review_status="needs_review" if reasons else "ok",
        review_reasons=reasons,
        transcription=transcription,
        usage=AiUsageOut(model=usage.model, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, calls=1)
        if usage
        else None,
    )


def mention_conflicts(mentions: list[VehicleMention], cars: list[TripCar]) -> list[str]:
    """Marcas que se dicen en el audio y que no aparecen en ningún carro (foto) del viaje."""
    car_makes = [make for car in cars for make in (car.brand, car.make_from_photo) if make]
    if not car_makes:
        return []
    conflicts = []
    for mention in mentions:
        if mention.make and not any(vin_service.makes_match(mention.make, make) for make in car_makes):
            label = " ".join(part for part in (mention.make, mention.model) if part)
            conflicts.append(f"El audio menciona un {label} que no está en las fotos del viaje")
    return conflicts


def trip_vehicle_mentions(db: Session, trip_id: str) -> list[VehicleMention]:
    mentions: list[VehicleMention] = []
    for record in intake_file_repository.list_for_trip(db, trip_id, kind="audio"):
        if record.status == "processed" and record.extraction:
            result = TripAudioResult.model_validate(record.extraction)
            if result.extraction is not None:
                mentions.extend(result.extraction.vehicle_mentions)
    return mentions


def flag_trip(trip: Trip, reasons: list[str]) -> None:
    """Pone el viaje en revisión; si ya lo estaba, suma los motivos nuevos."""
    if not reasons:
        return
    previous = trip.review_notes.split("\n") if trip.review_status == "needs_review" and trip.review_notes else []
    trip.review_notes = "\n".join(dict.fromkeys(previous + reasons))
    trip.review_status = "needs_review"


def apply_audio_to_trip(db: Session, trip: Trip, result: TripAudioResult, uploaded_by_staff: bool) -> list[str]:
    """Liga lo dicho al viaje: llena lo que falta y marca revisión donde no cuadra."""
    extraction = result.extraction
    if extraction is None:
        reasons = ["No se entendió nada en el audio"]
        flag_trip(trip, reasons)
        return reasons

    reasons: list[str] = []
    zones = {zone.id: zone for zone in zone_repository.list_all(db, limit=200)}

    for place, zone_id, trip_zone_id, text_field, verb in (
        (extraction.origin, result.origin_zone_id, trip.origin_zone_id, "origin_text", "salió de"),
        (extraction.destination, result.destination_zone_id, trip.destination_zone_id, "destination_text", "llegó a"),
    ):
        if place is None:
            continue
        setattr(trip, text_field, place.spoken)
        if zone_id is None:
            reasons.append(f"El audio dice que {verb} «{place.normalized}», que no es una zona registrada")
        elif zone_id != trip_zone_id:
            said, current = zones.get(zone_id), zones.get(trip_zone_id)
            reasons.append(
                f"El audio dice que {verb} {said.name if said else '?'}, pero el viaje tiene {current.name if current else '?'}"
            )

    if result.cost_amount is not None:
        if trip.amount is None:
            trip.amount = result.cost_amount
            trip.currency = result.cost_currency
            if not uploaded_by_staff:
                reasons.append("Monto dictado por el chofer: falta confirmarlo")
            if result.currency_assumed:
                reasons.append("No se dijo la moneda: se asumió colones")
        elif (round(float(trip.amount), 2), trip.currency) != (round(result.cost_amount, 2), result.cost_currency):
            reasons.append(
                f"El audio dice {format_money(result.cost_amount, result.cost_currency)}, "
                f"pero el viaje tiene {format_money(float(trip.amount), trip.currency)}"
            )

    if extraction.trip_date is not None and abs((extraction.trip_date - trip.started_at.date()).days) > 1:
        reasons.append(
            f"El audio habla del {extraction.trip_date:%d/%m/%Y}, pero el viaje es del {trip.started_at:%d/%m/%Y}"
        )
    reasons.extend(mention_conflicts(extraction.vehicle_mentions, trip_car_repository.list_for_trip(db, str(trip.id))))
    if extraction.confidence < CONFIDENCE_THRESHOLD:
        reasons.append(f"Extracción con poca seguridad ({extraction.confidence:.0%})")

    flag_trip(trip, reasons)
    return reasons


def _audio_out(
    record: IntakeFile, trip: Trip | None, trip_reasons: list[str] | None, duplicate: bool
) -> AudioIntakeOut:
    result = TripAudioResult.model_validate(record.extraction)
    linked = trip is not None and record.trip_id == trip.id
    return AudioIntakeOut(
        **result.model_dump(),
        intake_file_id=record.id,
        trip_id=record.trip_id,
        trip_review_status=trip.review_status if linked else None,
        trip_review_reasons=trip_reasons or [],
        duplicate=duplicate,
    )


def attach_audio_to_trip(db: Session, record: IntakeFile, trip: Trip, uploaded_by_staff: bool) -> list[str]:
    record.trip_id = trip.id
    reasons = apply_audio_to_trip(db, trip, TripAudioResult.model_validate(record.extraction), uploaded_by_staff)
    db.commit()
    return reasons


def ingest_audio(
    db: Session,
    *,
    data: bytes,
    user_id: str,
    trip: Trip | None,
    uploaded_by_staff: bool,
    transcriber: Transcriber,
    extractor: ClaudeExtractor,
    storage: SupabaseStorage,
    today: date | None = None,
) -> AudioIntakeOut:
    audio_format = audio_service.detect(data)
    file_sha256 = hashlib.sha256(data).hexdigest()
    record = intake_file_repository.get_by_sha256(db, file_sha256)

    if record is not None and record.status == "processed":
        # Audio repetido: no se vuelve a transcribir ni a extraer.
        reasons = None
        if trip is not None and record.trip_id is None:
            reasons = attach_audio_to_trip(db, record, trip, uploaded_by_staff)
        return _audio_out(record, trip, reasons, duplicate=True)

    if record is None:
        path = object_path("audios", file_sha256, audio_format.media_type)
        storage.upload(path, data, audio_format.media_type)
        record = intake_file_repository.add(
            db,
            IntakeFile(
                kind="audio",
                file_sha256=file_sha256,
                storage_path=path,
                mime_type=audio_format.media_type,
                size_bytes=len(data),
                status="failed",
                created_by=user_id,
            ),
        )

    zones = zone_repository.list_all(db, limit=200)
    zone_names = [zone.name for zone in zones]
    extraction, usage = None, None
    try:
        if record.transcript is None:
            transcription = transcriber.transcribe(
                data, f"nota.{audio_format.extension}", audio_format.media_type, build_prompt(zone_names)
            )
            record.transcript = transcription.text
            record.duration_seconds = transcription.duration_seconds
        if record.transcript.strip():
            extraction, usage = extractor.extract_trip(record.transcript, zone_names, today or costa_rica_today())
    except (TranscriptionError, ClaudeExtractionError) as exc:
        record.status = "failed"
        record.error = str(exc)
        db.commit()
        raise

    result = build_audio_result(
        record.transcript,
        TranscriptionOut(
            model=transcriber.model,
            duration_seconds=float(record.duration_seconds) if record.duration_seconds is not None else None,
        ),
        extraction,
        usage,
        zones,
    )
    record.status = "processed"
    record.error = None
    record.extraction = result.model_dump(mode="json")
    if usage is not None:
        record.ai_model = usage.model
        record.input_tokens = usage.input_tokens
        record.output_tokens = usage.output_tokens

    reasons = None
    if trip is not None:
        record.trip_id = trip.id
        reasons = apply_audio_to_trip(db, trip, result, uploaded_by_staff)
    db.commit()
    return _audio_out(record, trip, reasons, duplicate=False)
