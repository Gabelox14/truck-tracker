import base64
import logging
from dataclasses import dataclass
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.intake import VinPhotoExtraction
from app.services.image_service import PreparedImage

logger = logging.getLogger(__name__)

OutputT = TypeVar("OutputT", bound=BaseModel)

# Modelos que aceptan el respaldo del lado del servidor ("fallbacks": "default"),
# que reintenta en otro modelo si el primero rechaza la solicitud. Haiku no lo tiene.
_SERVER_FALLBACK_MODELS = {"claude-sonnet-5-5", "claude-opus-5-5"}
_SERVER_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_MAX_TOKENS = 8000

VIN_SYSTEM_PROMPT = """Lees fotos de vehículos para una empresa de grúas de Costa Rica que transporta carros nuevos y usados, muchos importados de Estados Unidos, Japón y Corea.

Transcribe el VIN (o el número de chasis) y anota lo que se ve del vehículo:
- Copia el VIN carácter por carácter tal como está impreso. No lo corrijas, no lo completes y no lo deduzcas de la marca o el modelo.
- Si un carácter no se distingue con certeza, pon "?" en su lugar. Si no hay ningún VIN ni número de chasis visible, vin_text es null.
- Los números de chasis japoneses (por ejemplo "GRJ150-0012345") también van en vin_text, tal cual.
- Marca, modelo y color salen de lo que se ve: logo, calcomanía, documento o carrocería. Si no se distinguen, null.
- vin_bbox es el rectángulo que encierra el VIN, en píxeles de esta imagen."""

_PHOTO_PROMPT = "Lee el VIN de esta foto."
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

    def read_vin_photo(self, image: PreparedImage, *, is_crop: bool = False) -> tuple[VinPhotoExtraction, ClaudeUsage]:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image.media_type,
                    "data": base64.standard_b64encode(image.data).decode("ascii"),
                },
            },
            {"type": "text", "text": _CROP_PROMPT if is_crop else _PHOTO_PROMPT},
        ]
        return self._parse("vin_photo", VIN_SYSTEM_PROMPT, content, VinPhotoExtraction)

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
