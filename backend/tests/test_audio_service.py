import pytest

from app.services import audio_service


@pytest.mark.parametrize(
    ("head", "media_type"),
    [
        (b"OggS" + bytes(28), "audio/ogg"),
        (b"RIFF" + bytes(4) + b"WAVE" + bytes(20), "audio/wav"),
        (b"fLaC" + bytes(28), "audio/flac"),
        (bytes([0x1A, 0x45, 0xDF, 0xA3]) + bytes(28), "audio/webm"),
        (bytes(4) + b"ftypM4A " + bytes(20), "audio/mp4"),
        (b"ID3" + bytes(29), "audio/mpeg"),
        (bytes([0xFF, 0xFB]) + bytes(30), "audio/mpeg"),
    ],
)
def test_detects_format_by_signature(head, media_type):
    assert audio_service.detect(head).media_type == media_type


def test_rejects_non_audio():
    with pytest.raises(audio_service.UnsupportedAudioError):
        audio_service.detect(b"%PDF-1.4 no soy audio")
