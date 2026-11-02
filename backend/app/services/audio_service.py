from dataclasses import dataclass


class UnsupportedAudioError(ValueError):
    pass


@dataclass(frozen=True)
class AudioFormat:
    media_type: str
    extension: str


OGG = AudioFormat("audio/ogg", "ogg")
MP3 = AudioFormat("audio/mpeg", "mp3")
M4A = AudioFormat("audio/mp4", "m4a")
WAV = AudioFormat("audio/wav", "wav")
WEBM = AudioFormat("audio/webm", "webm")
FLAC = AudioFormat("audio/flac", "flac")


def detect(data: bytes) -> AudioFormat:
    """Identifica el formato por su firma, sin confiar en el nombre ni en el
    Content-Type. Las notas de voz de WhatsApp son OGG con Opus."""
    head = data[:16]
    if head.startswith(b"OggS"):
        return OGG
    if head.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return WAV
    if head.startswith(b"fLaC"):
        return FLAC
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return WEBM
    if data[4:8] == b"ftyp":
        return M4A
    if head.startswith(b"ID3") or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return MP3
    raise UnsupportedAudioError("Formato de audio no soportado: usa OGG (WhatsApp), MP3, M4A, WAV, WebM o FLAC")
