import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Groq limita el prompt de Whisper a 224 tokens; con este tope de caracteres
# queda holgado en español.
_PROMPT_MAX_CHARS = 600
_BASE_PROMPT = (
    "Nota de voz de un chofer de grúa en Costa Rica sobre un viaje: de dónde salió, a dónde llegó, "
    "cuánto costó en colones o dólares (rojos, tejas, mil, cien mil) y qué carros llevaba "
    "(Toyota, Hyundai, Nissan, Kia, Mitsubishi, Suzuki, Honda). Lugares: San José, Alajuela, Heredia, "
    "Cartago, Puntarenas, Limón, Caldera, Moín, Guanacaste, Liberia"
)


class TranscriptionNotConfigured(RuntimeError):
    pass


class TranscriptionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Transcription:
    text: str
    duration_seconds: float | None
    model: str


def build_prompt(zone_names: list[str]) -> str:
    """Vocabulario que ayuda a escribir bien lugares y jerga de montos."""
    prompt = _BASE_PROMPT
    for name in zone_names:
        candidate = f"{prompt}, {name}"
        if len(candidate) > _PROMPT_MAX_CHARS:
            break
        prompt = candidate
    return prompt + "."


class Transcriber:
    """Endpoint /audio/transcriptions compatible con OpenAI (Groq, OpenAI)."""

    def __init__(self, base_url: str, api_key: str, model: str, http_client: httpx.Client | None = None):
        self._url = f"{base_url.rstrip('/')}/audio/transcriptions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self.model = model
        self._client = http_client or httpx.Client(timeout=120.0)

    def transcribe(self, data: bytes, filename: str, media_type: str, prompt: str) -> Transcription:
        # verbose_json trae la duración (para el costo); solo los modelos Whisper lo aceptan.
        response_format = "verbose_json" if "whisper" in self.model else "json"
        try:
            response = self._client.post(
                self._url,
                headers=self._headers,
                files={"file": (filename, data, media_type)},
                data={
                    "model": self.model,
                    "language": "es",
                    "prompt": prompt,
                    "response_format": response_format,
                    "temperature": "0",
                },
            )
        except httpx.HTTPError as exc:
            raise TranscriptionError("No se pudo conectar con el servicio de transcripción") from exc
        if response.status_code >= 400:
            logger.error("transcription failed status=%s body=%s", response.status_code, response.text[:300])
            raise TranscriptionError(f"El servicio de transcripción respondió con error {response.status_code}")
        body = response.json()
        duration = body.get("duration")
        logger.info("transcription model=%s duration_seconds=%s", self.model, duration)
        return Transcription(
            text=(body.get("text") or "").strip(),
            duration_seconds=float(duration) if duration is not None else None,
            model=self.model,
        )


_transcriber: Transcriber | None = None


def get_transcriber() -> Transcriber:
    global _transcriber
    if not settings.transcription_api_key:
        raise TranscriptionNotConfigured("Falta configurar TRANSCRIPTION_API_KEY en el backend")
    if _transcriber is None:
        _transcriber = Transcriber(
            settings.transcription_base_url, settings.transcription_api_key, settings.transcription_model
        )
    return _transcriber
