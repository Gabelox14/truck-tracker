import io
import math
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.schemas.intake import VinBox

# Límites de visión de la API de Claude para los modelos de alta resolución
# (Claude 4.7 en adelante, incluidos Sonnet 5.5 y Haiku 5.5): lo que pase de
# esto la API lo achica por su cuenta, así que lo achicamos antes nosotros y
# las coordenadas que devuelve el modelo corresponden a la imagen enviada.
MAX_LONG_EDGE = 2576
MAX_VISUAL_TOKENS = 4784
PATCH_PIXELS = 28
MAX_BASE64_BYTES = 10 * 1024 * 1024

# Un recorte del VIN se amplía hasta este lado largo: el texto ocupa más
# parches visuales y el modelo lo lee mejor.
CROP_TARGET_LONG_EDGE = 1400

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
_EXIF_ORIENTATION = 0x0112


class UnsupportedImageError(ValueError):
    pass


@dataclass(frozen=True)
class LoadedImage:
    image: Image.Image
    media_type: str
    original: bytes
    rotated: bool


@dataclass(frozen=True)
class PreparedImage:
    data: bytes
    media_type: str
    width: int
    height: int
    scale: float  # lado enviado / lado original


def load(data: bytes) -> LoadedImage:
    try:
        image = Image.open(io.BytesIO(data))
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise UnsupportedImageError("El archivo no es una imagen válida o es demasiado grande") from exc
    if image_format not in ALLOWED_FORMATS:
        raise UnsupportedImageError("Formato no soportado: usa JPEG, PNG o WebP")
    rotated = image.getexif().get(_EXIF_ORIENTATION, 1) != 1
    if rotated:
        image = ImageOps.exif_transpose(image)
    return LoadedImage(image=image, media_type=ALLOWED_FORMATS[image_format], original=data, rotated=rotated)


def visual_tokens(width: int, height: int) -> int:
    return math.ceil(width / PATCH_PIXELS) * math.ceil(height / PATCH_PIXELS)


def fit_size(width: int, height: int) -> tuple[int, int]:
    scale = min(1.0, MAX_LONG_EDGE / max(width, height))
    fitted = (max(1, round(width * scale)), max(1, round(height * scale)))
    while visual_tokens(*fitted) > MAX_VISUAL_TOKENS:
        scale *= 0.99
        fitted = (max(1, int(width * scale)), max(1, int(height * scale)))
    return fitted


def _base64_size(byte_count: int) -> int:
    return 4 * math.ceil(byte_count / 3)


def _encode_jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=92, optimize=True)
    return buffer.getvalue()


def prepare(loaded: LoadedImage) -> PreparedImage:
    """Solo recodifica si la foto pasa los límites de la API o venía rotada."""
    width, height = loaded.image.size
    target = fit_size(width, height)
    if target == (width, height) and not loaded.rotated and _base64_size(len(loaded.original)) <= MAX_BASE64_BYTES:
        return PreparedImage(loaded.original, loaded.media_type, width, height, 1.0)
    resized = loaded.image if target == (width, height) else loaded.image.resize(target, Image.Resampling.LANCZOS)
    return PreparedImage(_encode_jpeg(resized), "image/jpeg", target[0], target[1], target[0] / width)


def crop_region(loaded: LoadedImage, box: VinBox, scale: float) -> PreparedImage | None:
    """Recorta la zona del VIN de la foto original (resolución completa) usando
    el rectángulo que el modelo marcó sobre la imagen enviada."""
    x0, y0, x1, y1 = (value / scale for value in (box.x_min, box.y_min, box.x_max, box.y_max))
    if x1 <= x0 or y1 <= y0:
        return None
    box_height = y1 - y0
    pad_x = (x1 - x0) * 0.1 + box_height
    pad_y = box_height
    width, height = loaded.image.size
    left, top = max(0, int(x0 - pad_x)), max(0, int(y0 - pad_y))
    right, bottom = min(width, int(x1 + pad_x)), min(height, int(y1 + pad_y))
    if right - left < 8 or bottom - top < 8:
        return None

    crop = loaded.image.crop((left, top, right, bottom))
    long_edge = max(crop.size)
    if long_edge < CROP_TARGET_LONG_EDGE:
        factor = CROP_TARGET_LONG_EDGE / long_edge
        crop = crop.resize((round(crop.width * factor), round(crop.height * factor)), Image.Resampling.LANCZOS)
    target = fit_size(*crop.size)
    if target != crop.size:
        crop = crop.resize(target, Image.Resampling.LANCZOS)
    return PreparedImage(_encode_jpeg(crop), "image/jpeg", crop.width, crop.height, 1.0)
