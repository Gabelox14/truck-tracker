import io

from PIL import Image

from app.schemas.intake import VinBox, VinPhotoExtraction
from app.services.claude_service import ClaudeUsage


def make_jpeg(width: int = 800, height: int = 600, color=(200, 200, 200), exif_orientation: int | None = None) -> bytes:
    image = Image.new("RGB", (width, height), color)
    buffer = io.BytesIO()
    if exif_orientation is None:
        image.save(buffer, format="JPEG")
    else:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def make_extraction(**overrides) -> VinPhotoExtraction:
    values = {
        "vin_text": "1HGCM82633A004352",
        "vin_location": "parabrisas",
        "make": "Honda",
        "model": "Accord",
        "color": "gris",
        "image_quality": "buena",
        "confidence": 0.95,
        "vin_bbox": VinBox(x_min=100, y_min=200, x_max=500, y_max=240),
        "notes": None,
    }
    values.update(overrides)
    return VinPhotoExtraction(**values)


class FakeExtractor:
    """Reemplaza a Claude: devuelve las lecturas dadas, en orden."""

    def __init__(self, *readings: VinPhotoExtraction, model: str = "claude-sonnet-5-5"):
        self.readings = list(readings)
        self.model = model
        self.calls: list[dict] = []

    def read_vin_photo(self, image, *, is_crop: bool = False):
        self.calls.append({"is_crop": is_crop, "width": image.width, "height": image.height})
        reading = self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]
        return reading, ClaudeUsage(model=self.model, input_tokens=1500, output_tokens=200)
