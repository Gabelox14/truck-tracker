import httpx
import pytest

from app.services import transcription_service
from app.services.transcription_service import Transcriber, TranscriptionError, build_prompt


def _transcriber(handler, model="whisper-large-v3"):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Transcriber("https://api.groq.test/openai/v1", "key-123", model, http_client=client)


def test_sends_spanish_whisper_request_and_reads_duration():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.content
        return httpx.Response(200, json={"text": " Salí del Coyol, 50 rojos ", "duration": 37.5})

    result = _transcriber(handler).transcribe(b"OggS...", "nota.ogg", "audio/ogg", "vocabulario")
    assert seen["url"] == "https://api.groq.test/openai/v1/audio/transcriptions"
    assert seen["auth"] == "Bearer key-123"
    for field in (b'name="model"', b"whisper-large-v3", b'name="language"', b"es", b"verbose_json", b"vocabulario"):
        assert field in seen["body"]
    assert result.text == "Salí del Coyol, 50 rojos"
    assert result.duration_seconds == 37.5


def test_non_whisper_models_ask_for_plain_json():
    seen = {}

    def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, json={"text": "hola"})

    result = _transcriber(handler, model="gpt-4o-transcribe").transcribe(b"x", "nota.ogg", "audio/ogg", "")
    assert b"verbose_json" not in seen["body"]
    assert result.duration_seconds is None


def test_errors_become_transcription_error():
    with pytest.raises(TranscriptionError):
        _transcriber(lambda request: httpx.Response(429, json={"error": "rate"})).transcribe(b"x", "n.ogg", "audio/ogg", "")

    def boom(request):
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(TranscriptionError):
        _transcriber(boom).transcribe(b"x", "n.ogg", "audio/ogg", "")


def test_prompt_includes_zones_and_stays_short():
    prompt = build_prompt(["Coyol", "Lindora", "Uruca"])
    assert "Coyol" in prompt and "Uruca" in prompt and "rojos" in prompt
    long_prompt = build_prompt([f"Zona número {i}" for i in range(200)])
    assert len(long_prompt) <= 601


def test_missing_key_is_reported(monkeypatch):
    monkeypatch.setattr(transcription_service.settings, "transcription_api_key", None)
    with pytest.raises(transcription_service.TranscriptionNotConfigured):
        transcription_service.get_transcriber()
