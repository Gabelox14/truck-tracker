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


class FakeStorage:
    """Bucket en memoria."""

    def __init__(self):
        self.bucket = "intake-test"
        self.objects: dict[str, tuple[bytes, str]] = {}

    def upload(self, path: str, data: bytes, content_type: str) -> None:
        self.objects[path] = (data, content_type)

    def download(self, path: str) -> bytes:
        return self.objects[path][0]

    def signed_url(self, path: str, expires_in: int = 600) -> str:
        return f"http://storage.test/{self.bucket}/{path}?token=t&expires_in={expires_in}"

    def delete(self, path: str) -> None:
        self.objects.pop(path, None)


class FailingExtractor:
    model = "claude-sonnet-5-5"

    def __init__(self, message: str = "Claude respondió con error 529"):
        self.message = message

    def read_vin_photo(self, image, *, is_crop: bool = False):
        from app.services.claude_service import ClaudeExtractionError

        raise ClaudeExtractionError(self.message)


def seed_fleet(db):
    """Admin, dos choferes con su perfil, un camión, dos zonas y un viaje del primer chofer."""
    import uuid
    from types import SimpleNamespace

    from sqlalchemy import text

    from app.models import Driver, Profile, Trip, Truck, Zone

    admin_id, driver_user_id, other_user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    suffix = uuid.uuid4().hex[:6]
    for user_id in (admin_id, driver_user_id, other_user_id):
        db.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": user_id})
    db.add_all(
        [
            Profile(id=admin_id, email="admin@test", full_name="Admin Test", cedula=f"a{suffix}", role="admin"),
            Profile(id=driver_user_id, email="chofer@test", full_name="Chofer Uno", cedula=f"d{suffix}", role="driver"),
            Profile(id=other_user_id, email="otro@test", full_name="Chofer Dos", cedula=f"o{suffix}", role="driver"),
        ]
    )
    db.flush()
    driver = Driver(profile_id=driver_user_id, full_name="Chofer Uno")
    other_driver = Driver(profile_id=other_user_id, full_name="Chofer Dos")
    truck = Truck(plate=f"TST-{suffix}", code="T1", brand="Isuzu")
    origin = Zone(name=f"Coyol {suffix}")
    destination = Zone(name=f"Uruca {suffix}")
    db.add_all([driver, other_driver, truck, origin, destination])
    db.flush()
    trip = Trip(driver_id=driver.id, truck_id=truck.id, origin_zone_id=origin.id, destination_zone_id=destination.id)
    db.add(trip)
    db.flush()
    return SimpleNamespace(
        admin_id=str(admin_id),
        driver_user_id=str(driver_user_id),
        other_user_id=str(other_user_id),
        driver=driver,
        other_driver=other_driver,
        truck=truck,
        origin=origin,
        destination=destination,
        trip=trip,
    )
