import io

import pytest
from PIL import Image

from app.schemas.intake import VinBox
from app.services import image_service
from tests.helpers import make_jpeg


def test_small_photo_is_sent_untouched():
    data = make_jpeg(1600, 1200)
    prepared = image_service.prepare(image_service.load(data))
    assert prepared.data == data
    assert prepared.media_type == "image/jpeg"
    assert prepared.scale == 1.0


def test_large_photo_is_resized_to_api_limits():
    loaded = image_service.load(make_jpeg(4032, 3024))
    prepared = image_service.prepare(loaded)
    assert max(prepared.width, prepared.height) <= image_service.MAX_LONG_EDGE
    assert image_service.visual_tokens(prepared.width, prepared.height) <= image_service.MAX_VISUAL_TOKENS
    assert prepared.scale == pytest.approx(prepared.width / 4032)
    sent = Image.open(io.BytesIO(prepared.data))
    assert sent.size == (prepared.width, prepared.height)


def test_rotated_phone_photo_is_straightened():
    # Orientación 6 = la cámara guardó la foto acostada; se ve parada.
    loaded = image_service.load(make_jpeg(1200, 800, exif_orientation=6))
    assert loaded.rotated is True
    assert loaded.image.size == (800, 1200)
    prepared = image_service.prepare(loaded)
    assert (prepared.width, prepared.height) == (800, 1200)


def test_png_and_webp_are_accepted():
    for fmt, media_type in (("PNG", "image/png"), ("WEBP", "image/webp")):
        buffer = io.BytesIO()
        Image.new("RGB", (300, 200)).save(buffer, format=fmt)
        assert image_service.load(buffer.getvalue()).media_type == media_type


def test_gif_and_garbage_are_rejected():
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="GIF")
    with pytest.raises(image_service.UnsupportedImageError):
        image_service.load(buffer.getvalue())
    with pytest.raises(image_service.UnsupportedImageError):
        image_service.load(b"no soy una imagen")


def test_crop_maps_box_back_to_full_resolution():
    loaded = image_service.load(make_jpeg(4032, 3024))
    prepared = image_service.prepare(loaded)
    box_original = (1000, 1500, 2000, 1580)
    box_sent = VinBox(
        x_min=round(box_original[0] * prepared.scale),
        y_min=round(box_original[1] * prepared.scale),
        x_max=round(box_original[2] * prepared.scale),
        y_max=round(box_original[3] * prepared.scale),
    )
    crop = image_service.crop_region(loaded, box_sent, prepared.scale)
    assert crop is not None
    assert max(crop.width, crop.height) >= image_service.CROP_TARGET_LONG_EDGE
    assert image_service.visual_tokens(crop.width, crop.height) <= image_service.MAX_VISUAL_TOKENS
    # El recorte (con margen) es más ancho que alto, como una línea de VIN.
    assert crop.width > crop.height


def test_crop_ignores_degenerate_box():
    loaded = image_service.load(make_jpeg(800, 600))
    assert image_service.crop_region(loaded, VinBox(x_min=50, y_min=50, x_max=50, y_max=80), 1.0) is None
