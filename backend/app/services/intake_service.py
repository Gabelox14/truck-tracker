import hashlib
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.time import costa_rica_today
from app.models.intake_file import IntakeFile
from app.models.trip import Trip
from app.models.trip_car import TripCar
from app.repositories import intake_file_repository, trip_car_repository
from app.schemas.intake import AiUsageOut, NhtsaDecodeOut, VinPhotoExtraction, VinPhotoIntakeOut, VinPhotoResult
from app.services import audio_intake_service, image_service, nhtsa_service, vin_service
from app.services.claude_service import ClaudeExtractionError, ClaudeExtractor, ClaudeUsage
from app.services.storage_service import SupabaseStorage, object_path

CONFIDENCE_THRESHOLD = 0.7

NhtsaDecoder = Callable[[str], NhtsaDecodeOut | None]


def _needs_second_look(extraction: VinPhotoExtraction, check: vin_service.VinCheck | None) -> bool:
    if check is None or extraction.vin_bbox is None:
        return False
    if "?" in check.normalized or extraction.confidence < CONFIDENCE_THRESHOLD:
        return True
    return len(check.normalized) == vin_service.VIN_LENGTH and (
        not check.is_valid or check.check_digit_ok is False
    )


def _reading_score(extraction: VinPhotoExtraction, check: vin_service.VinCheck | None) -> tuple:
    if check is None:
        return (False, False, False, 0.0)
    return (check.is_valid, check.check_digit_ok is True, "?" not in check.normalized, extraction.confidence)


def _review_reasons(
    extraction: VinPhotoExtraction,
    check: vin_service.VinCheck | None,
    nhtsa: NhtsaDecodeOut | None,
    vin_make: str | None,
    make_matches: bool | None,
    vin_year: int | None,
) -> list[str]:
    reasons: list[str] = []
    if check is None:
        reasons.append("No se encontró un VIN en la foto")
    elif "?" in check.normalized:
        reasons.append("Hay caracteres del VIN que no se pudieron leer")
    elif not check.is_valid:
        reasons.append("No es un VIN de 17 caracteres (puede ser un número de chasis)")
    elif check.check_digit_ok is False:
        reasons.append("El dígito verificador no cuadra (normal en carros fuera de Norteamérica)")

    # Sin marca por NHTSA ni por la tabla de fabricantes no hay con qué confirmar el VIN.
    if check is not None and check.is_valid and vin_make is None:
        if nhtsa is None:
            reasons.append("No se pudo consultar NHTSA para confirmar el VIN")
        else:
            reasons.append(nhtsa_service.describe_problem(nhtsa))
    if make_matches is False:
        reasons.append(f"La marca de la foto ({extraction.make}) no coincide con la del VIN ({vin_make})")
    if extraction.model_year and vin_year and abs(extraction.model_year - vin_year) > 1:
        reasons.append(f"El año de la etiqueta ({extraction.model_year}) no coincide con el del VIN ({vin_year})")
    if check is not None and extraction.confidence < CONFIDENCE_THRESHOLD:
        reasons.append(f"Lectura con poca seguridad ({extraction.confidence:.0%})")
    if extraction.image_quality == "mala":
        reasons.append("La foto es de mala calidad")
    return reasons


def _total_usage(usages: list[ClaudeUsage]) -> AiUsageOut:
    return AiUsageOut(
        model=usages[-1].model,
        input_tokens=sum(u.input_tokens for u in usages),
        output_tokens=sum(u.output_tokens for u in usages),
        calls=len(usages),
    )


def process_vin_photo(
    loaded: image_service.LoadedImage,
    extractor: ClaudeExtractor,
    decode_vin: NhtsaDecoder | None = None,
) -> VinPhotoResult:
    decode_vin = decode_vin or nhtsa_service.decode_vin
    prepared = image_service.prepare(loaded)
    extraction, usage = extractor.read_vin_photo(prepared)
    usages = [usage]
    check = vin_service.analyze(extraction.vin_text) if extraction.vin_text else None

    if _needs_second_look(extraction, check):
        crop = image_service.crop_region(loaded, extraction.vin_bbox, prepared.scale)
        if crop is not None:
            closer, closer_usage = extractor.read_vin_photo(crop, is_crop=True)
            usages.append(closer_usage)
            closer_check = vin_service.analyze(closer.vin_text) if closer.vin_text else None
            if _reading_score(closer, closer_check) > _reading_score(extraction, check):
                # La marca, el color y la calidad se quedan con lo que se vio en la foto completa.
                extraction = extraction.model_copy(
                    update={
                        "vin_text": closer.vin_text,
                        "confidence": closer.confidence,
                        "notes": closer.notes or extraction.notes,
                    }
                )
                check = closer_check

    nhtsa = decode_vin(check.normalized) if check is not None and check.is_valid else None
    wmi_make = vin_service.make_from_wmi(check.normalized) if check is not None and check.is_valid else None
    vin_make = (nhtsa.make if nhtsa is not None and nhtsa.make else None) or wmi_make
    make_matches = vin_service.makes_match(extraction.make, vin_make) if extraction.make and vin_make else None
    vin_year = None
    if check is not None and check.is_valid:
        # NHTSA resuelve bien el ciclo de 30 años solo cuando decodifica limpio;
        # si no, se toma el ciclo más reciente (los carros que se transportan son nuevos).
        if nhtsa is not None and nhtsa.model_year and nhtsa_service.decoded_cleanly(nhtsa):
            vin_year = nhtsa.model_year
        else:
            vin_year = vin_service.latest_model_year(check.normalized, costa_rica_today().year)
    reasons = _review_reasons(extraction, check, nhtsa, vin_make, make_matches, vin_year)

    return VinPhotoResult(
        vin_text=extraction.vin_text,
        vin_location=extraction.vin_location,
        make=extraction.make,
        model=extraction.model,
        color=extraction.color,
        image_quality=extraction.image_quality,
        confidence=extraction.confidence,
        notes=extraction.notes,
        vin=check.normalized if check is not None else None,
        vin_valid=check.is_valid if check is not None else False,
        check_digit_ok=check.check_digit_ok if check is not None else None,
        nhtsa=nhtsa,
        wmi_make=wmi_make,
        model_year=extraction.model_year or vin_year,
        make_matches=make_matches,
        review_status="needs_review" if reasons else "ok",
        review_reasons=reasons,
        usage=_total_usage(usages),
    )


def car_fields_from_vin_result(result: VinPhotoResult) -> dict:
    """Marca y modelo de NHTSA solo si el VIN pasó el dígito verificador; si no,
    manda lo que se vio en la foto."""
    nhtsa = result.nhtsa
    trust_vin = result.check_digit_ok is True
    vin_make = (nhtsa.make if nhtsa is not None and nhtsa.make else None) or result.wmi_make
    vin_make = vin_service.display_make(vin_make) if vin_make else None
    photo_make = vin_service.display_make(result.make) if result.make else None
    nhtsa_model = nhtsa.model if nhtsa is not None else None
    return {
        "brand": (vin_make if trust_vin else None) or photo_make or vin_make,
        "make_from_photo": result.make,
        "model": (nhtsa_model if trust_vin else None) or result.model or nhtsa_model,
        "model_year": result.model_year,
        "color": result.color,
        "vin": result.vin,
        "vin_raw": result.vin_text,
        "vin_valid": result.vin_valid if result.vin else None,
        "check_digit_ok": result.check_digit_ok,
        "ocr_confidence": round(result.confidence, 2) if result.vin_text else None,
        "review_status": result.review_status,
        "review_notes": "\n".join(result.review_reasons) or None,
    }


def _mention_mismatch(fields: dict, mentions: list) -> str | None:
    """Si la nota de voz del viaje nombra marcas y la de este carro no es ninguna."""
    said = [mention.make for mention in mentions if mention.make]
    makes = [make for make in (fields["brand"], fields["make_from_photo"]) if make]
    if not said or not makes:
        return None
    if any(vin_service.makes_match(make, mention) for make in makes for mention in said):
        return None
    return f"La marca no coincide con lo dicho en la nota de voz ({', '.join(said)})"


def _add_car_from_photo(db: Session, record: IntakeFile, trip: Trip, user_id: str) -> TripCar:
    result = VinPhotoResult.model_validate(record.extraction)
    record.trip_id = trip.id
    fields = car_fields_from_vin_result(result)
    mismatch = _mention_mismatch(fields, audio_intake_service.trip_vehicle_mentions(db, str(trip.id)))
    if mismatch:
        fields["review_status"] = "needs_review"
        fields["review_notes"] = "\n".join(filter(None, [fields["review_notes"], mismatch]))
    return trip_car_repository.add(
        db,
        TripCar(trip_id=trip.id, photo_file_id=record.id, created_by=user_id, **fields),
    )


def _intake_out(record: IntakeFile, car: TripCar | None, duplicate: bool) -> VinPhotoIntakeOut:
    result = VinPhotoResult.model_validate(record.extraction)
    return VinPhotoIntakeOut(
        **result.model_dump(),
        intake_file_id=record.id,
        trip_id=record.trip_id,
        trip_car_id=car.id if car is not None else None,
        duplicate=duplicate,
    )


def attach_photo_to_trip(db: Session, record: IntakeFile, trip: Trip, user_id: str) -> TripCar:
    """Liga una foto ya procesada a un viaje creando su carro (o devuelve el existente)."""
    car = trip_car_repository.get_by_photo(db, str(record.id))
    if car is None:
        car = _add_car_from_photo(db, record, trip, user_id)
    db.commit()
    return car


def ingest_vin_photo(
    db: Session,
    *,
    data: bytes,
    user_id: str,
    trip: Trip | None,
    extractor: ClaudeExtractor,
    storage: SupabaseStorage,
    decode_vin: NhtsaDecoder | None = None,
) -> VinPhotoIntakeOut:
    loaded = image_service.load(data)
    file_sha256 = hashlib.sha256(data).hexdigest()
    record = intake_file_repository.get_by_sha256(db, file_sha256)

    if record is not None and record.status == "processed":
        # Archivo repetido: no se vuelve a pagar la lectura. Si llega con un
        # viaje y todavía no estaba ligado a otro, se liga ahora.
        car = trip_car_repository.get_by_photo(db, str(record.id))
        if trip is not None and car is None and record.trip_id in (None, trip.id):
            car = _add_car_from_photo(db, record, trip, user_id)
            db.commit()
        return _intake_out(record, car, duplicate=True)

    if record is None:
        path = object_path("vin-photos", file_sha256, loaded.media_type)
        storage.upload(path, data, loaded.media_type)
        record = intake_file_repository.add(
            db,
            IntakeFile(
                kind="vin_photo",
                file_sha256=file_sha256,
                storage_path=path,
                mime_type=loaded.media_type,
                size_bytes=len(data),
                status="failed",
                created_by=user_id,
            ),
        )

    try:
        result = process_vin_photo(loaded, extractor, decode_vin)
    except ClaudeExtractionError as exc:
        record.status = "failed"
        record.error = str(exc)
        db.commit()
        raise

    record.status = "processed"
    record.error = None
    record.extraction = result.model_dump(mode="json")
    record.ai_model = result.usage.model
    record.input_tokens = result.usage.input_tokens
    record.output_tokens = result.usage.output_tokens
    car = _add_car_from_photo(db, record, trip, user_id) if trip is not None else None
    db.commit()
    return _intake_out(record, car, duplicate=False)
