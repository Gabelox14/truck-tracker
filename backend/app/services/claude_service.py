import base64
import logging
from dataclasses import dataclass
from datetime import date
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.intake import TripAudioExtraction, VinPhotoExtraction
from app.services.image_service import PreparedImage

logger = logging.getLogger(__name__)

OutputT = TypeVar("OutputT", bound=BaseModel)

# Modelos que aceptan el respaldo del lado del servidor ("fallbacks": "default"),
# que reintenta en otro modelo si el primero rechaza la solicitud. Haiku no lo tiene.
_SERVER_FALLBACK_MODELS = {"claude-sonnet-5-5", "claude-opus-5-5"}
_SERVER_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_MAX_TOKENS = 8000

VIN_SYSTEM_PROMPT = """Lees fotos de vehículos para una empresa de grúas de Costa Rica que transporta carros nuevos y usados, muchos importados de Estados Unidos, Japón, India, China y Corea.

Puede llegar una sola foto o varias del mismo vehículo (por ejemplo la etiqueta o la placa del VIN y el carro por detrás). Transcribe el VIN (o el número de chasis) y anota lo que se ve del vehículo usando todas las fotos:
- Copia el VIN carácter por carácter tal como está impreso. No lo corrijas, no lo completes y no lo deduzcas de la marca o el modelo.
- Si un carácter no se distingue con certeza, pon "?" en su lugar. Si no hay ningún VIN ni número de chasis visible, vin_text es null.
- Los números de chasis japoneses (por ejemplo "GRJ150-0012345") también van en vin_text, tal cual.
- Marca, modelo y color salen de lo que se ve: logo, insignia del modelo en la carrocería, calcomanía o documento. Las placas de fábrica traen un código de tipo (por ejemplo "FL61S"), que no es el modelo: el modelo es el nombre comercial que se lee en el carro. Si no se distinguen, null.
- vin_image es el número de la foto donde está el VIN y vin_bbox el rectángulo que lo encierra, en píxeles de esa foto."""

TRIP_SYSTEM_PROMPT = """Extraes los datos de un viaje de grúa de la transcripción de una nota de voz de un chofer en Costa Rica.

- No inventes nada: lo que no se dice queda en null. La transcripción puede tener errores; interpreta lo que el chofer quiso decir (por ejemplo "France" es el Suzuki Fronx y "Espresso" el Suzuki S-Presso).
- Montos en jerga costarricense: un "rojo" es un billete de mil colones ("50 rojos" = 50000 CRC), una "teja" son 100 colones y un "melón" es un millón de colones. Si dice dólares, la moneda es USD. Si da un número sin decir ni dar a entender la moneda, cost_amount lleva el número y cost_currency es null.
- Si dice que el monto es "cada uno" o por vehículo, cost_amount es el monto de un vehículo y cost_per_vehicle es true; si es el total del viaje, cost_per_vehicle es false.
- La unidad es el camión ("unidad M2"); el chofer es la persona que maneja; quien lo solicita es el cliente que pidió el traslado.
- Lugares: spoken es como lo dijo; normalized es el nombre correcto del lugar en Costa Rica; zone es el nombre exacto de una de las zonas de la empresa (lista abajo) solo si el lugar es esa zona.
- trip_date: usa la fecha de hoy que se indica para resolver "hoy", "ayer" o un día de la semana."""

_PHOTO_PROMPT = "Lee el VIN de esta foto."
_PHOTOS_PROMPT = "Estas {count} fotos son del mismo vehículo. Lee el VIN y anota el vehículo usando todas."
_CROP_PROMPT = (
    "Esta imagen es un recorte ampliado de la zona del VIN de una foto. "
    "Transcribe el VIN con el mismo cuidado; si el recorte no muestra el vehículo, deja marca, modelo y color en null."
)


class ClaudeNotConfigured(RuntimeError):
    pass


class ClaudeExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClaudeUsage:
    model: str
    input_tokens: int
    output_tokens: int


class ClaudeExtractor:
    def __init__(self, client: anthropic.Anthropic, model: str, effort: str):
        self._client = client
        self.model = model
        self.effort = effort

    def read_vin_photo(
        self, images: list[PreparedImage], *, is_crop: bool = False
    ) -> tuple[VinPhotoExtraction, ClaudeUsage]:
        content: list[dict] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image.media_type,
                    "data": base64.standard_b64encode(image.data).decode("ascii"),
                },
            }
            for image in images
        ]
        if is_crop:
            prompt = _CROP_PROMPT
        elif len(images) > 1:
            prompt = _PHOTOS_PROMPT.format(count=len(images))
        else:
            prompt = _PHOTO_PROMPT
        content.append({"type": "text", "text": prompt})
        return self._parse("vin_photo", VIN_SYSTEM_PROMPT, content, VinPhotoExtraction)

    def extract_trip(
        self, transcript: str, zone_names: list[str], today: date
    ) -> tuple[TripAudioExtraction, ClaudeUsage]:
        zones = ", ".join(zone_names) if zone_names else "(ninguna registrada)"
        text = (
            f"Zonas de la empresa: {zones}\n"
            f"Fecha de hoy: {today.isoformat()}\n\n"
            f"Transcripción:\n{transcript}"
        )
        return self._parse("trip_audio", TRIP_SYSTEM_PROMPT, [{"type": "text", "text": text}], TripAudioExtraction)

    def _parse(self, kind: str, system: str, content: list, output_format: type[OutputT]) -> tuple[OutputT, ClaudeUsage]:
        request = {
            "model": self.model,
            "max_tokens": _MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": content}],
            "output_config": {"effort": self.effort},
            "output_format": output_format,
        }
        try:
            if self.model in _SERVER_FALLBACK_MODELS:
                response = self._client.beta.messages.parse(
                    **request, betas=[_SERVER_FALLBACK_BETA], fallbacks="default"
                )
            else:
                response = self._client.messages.parse(**request)
        except ValidationError as exc:
            raise ClaudeExtractionError("La respuesta de Claude no tiene el formato esperado") from exc
        except anthropic.APIConnectionError as exc:
            raise ClaudeExtractionError("No se pudo conectar con Claude") from exc
        except anthropic.RateLimitError as exc:
            raise ClaudeExtractionError("Claude está saturado; intenta de nuevo en un minuto") from exc
        except anthropic.APIStatusError as exc:
            logger.error("claude %s failed status=%s body=%s", kind, exc.status_code, exc.message)
            raise ClaudeExtractionError(f"Claude respondió con error {exc.status_code}") from exc

        usage = ClaudeUsage(
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        logger.info(
            "claude %s model=%s input_tokens=%d output_tokens=%d stop=%s request_id=%s",
            kind,
            usage.model,
            usage.input_tokens,
            usage.output_tokens,
            response.stop_reason,
            getattr(response, "_request_id", None),
        )
        if response.stop_reason == "refusal":
            raise ClaudeExtractionError("Claude no quiso procesar este archivo")
        if response.stop_reason == "max_tokens":
            raise ClaudeExtractionError("La respuesta de Claude quedó incompleta")
        parsed = response.parsed_output
        if parsed is None:
            raise ClaudeExtractionError("Claude no devolvió datos")
        return parsed, usage


_extractor: ClaudeExtractor | None = None


def get_extractor() -> ClaudeExtractor:
    global _extractor
    if not settings.anthropic_api_key:
        raise ClaudeNotConfigured("Falta configurar ANTHROPIC_API_KEY en el backend")
    if _extractor is None:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=90.0)
        _extractor = ClaudeExtractor(client, settings.anthropic_model, settings.anthropic_effort)
    return _extractor
