from collections.abc import Callable

from app.schemas.intake import AiUsageOut, NhtsaDecodeOut, VinPhotoExtraction, VinPhotoResult
from app.services import image_service, nhtsa_service, vin_service
from app.services.claude_service import ClaudeExtractor, ClaudeUsage

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
    make_matches: bool | None,
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

    if check is not None and check.is_valid:
        if nhtsa is None:
            reasons.append("No se pudo consultar NHTSA para confirmar el VIN")
        elif nhtsa.make is None:
            reasons.append(nhtsa_service.describe_problem(nhtsa))
    if make_matches is False:
        reasons.append(f"La marca de la foto ({extraction.make}) no coincide con la del VIN ({nhtsa.make})")
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
    data: bytes,
    extractor: ClaudeExtractor,
    decode_vin: NhtsaDecoder | None = None,
) -> VinPhotoResult:
    decode_vin = decode_vin or nhtsa_service.decode_vin
    loaded = image_service.load(data)
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
    make_matches = (
        vin_service.makes_match(extraction.make, nhtsa.make)
        if extraction.make and nhtsa is not None and nhtsa.make
        else None
    )
    reasons = _review_reasons(extraction, check, nhtsa, make_matches)

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
        make_matches=make_matches,
        review_status="needs_review" if reasons else "ok",
        review_reasons=reasons,
        usage=_total_usage(usages),
    )
