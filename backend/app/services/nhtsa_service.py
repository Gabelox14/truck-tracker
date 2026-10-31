import logging
import threading
from collections import OrderedDict

import httpx

from app.core.config import settings
from app.schemas.intake import NhtsaDecodeOut

logger = logging.getLogger(__name__)

DECODE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}"
_CACHE_MAX_ENTRIES = 512

_cache: OrderedDict[str, NhtsaDecodeOut] = OrderedDict()
_cache_lock = threading.Lock()

_ERROR_TEXT_ES = {
    "7": "NHTSA no tiene registrado al fabricante (vehículo no vendido en EE. UU.)",
    "8": "NHTSA no tiene detalles de este VIN",
}


def _value(row: dict, key: str) -> str | None:
    value = (row.get(key) or "").strip()
    return value or None


def decode_vin(vin: str, http_client: httpx.Client | None = None) -> NhtsaDecodeOut | None:
    """Decodifica con vPIC (gratis, sin llave). None si la consulta falla."""
    with _cache_lock:
        cached = _cache.get(vin)
        if cached is not None:
            _cache.move_to_end(vin)
            return cached

    client = http_client or httpx.Client(timeout=settings.nhtsa_timeout_seconds)
    try:
        response = client.get(DECODE_URL.format(vin=vin), params={"format": "json"})
        response.raise_for_status()
        results = response.json().get("Results") or []
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("NHTSA decode failed for %s: %s", vin, exc)
        return None
    finally:
        if http_client is None:
            client.close()

    if not results:
        return None
    row = results[0]
    model_year = _value(row, "ModelYear")
    decoded = NhtsaDecodeOut(
        make=_value(row, "Make"),
        model=_value(row, "Model"),
        model_year=int(model_year) if model_year and model_year.isdigit() else None,
        error_code=_value(row, "ErrorCode"),
        error_text=_value(row, "ErrorText"),
    )
    with _cache_lock:
        _cache[vin] = decoded
        if len(_cache) > _CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)
    return decoded


def describe_problem(decoded: NhtsaDecodeOut) -> str:
    codes = [code.strip() for code in (decoded.error_code or "").split(",") if code.strip()]
    for code in codes:
        if code in _ERROR_TEXT_ES:
            return _ERROR_TEXT_ES[code]
    return f"NHTSA no reconoce este VIN ({decoded.error_text})" if decoded.error_text else "NHTSA no reconoce este VIN"


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
