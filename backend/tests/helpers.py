import io

from PIL import Image

from app.schemas.intake import PlaceExtraction, TripAudioExtraction, VehicleMention, VinBox, VinPhotoExtraction
from app.services.claude_service import ClaudeUsage
from app.services.transcription_service import Transcription


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

    def __init__(self, *readings: VinPhotoExtraction, trip_readings=(), model: str = "claude-sonnet-5-5"):
        self.readings = list(readings)
        self.trip_readings = list(trip_readings)
        self.model = model
        self.calls: list[dict] = []
        self.trip_calls: list[dict] = []

    def extract_trip(self, transcript, zone_names, today):
        self.trip_calls.append({"transcript": transcript, "zone_names": zone_names, "today": today})
        reading = self.trip_readings.pop(0) if len(self.trip_readings) > 1 else self.trip_readings[0]
        return reading, ClaudeUsage(model=self.model, input_tokens=600, output_tokens=150)

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

    def extract_trip(self, transcript, zone_names, today):
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


def place(spoken: str, normalized: str, zone: str | None) -> PlaceExtraction:
    return PlaceExtraction(spoken=spoken, normalized=normalized, zone=zone)


def make_trip_extraction(**overrides) -> TripAudioExtraction:
    values = {
        "origin": place("el Coyol", "El Coyol, Alajuela", "Coyol"),
        "destination": place("la Uruca", "La Uruca, San José", "Uruca"),
        "cost_amount": 50000,
        "cost_currency": "CRC",
        "cost_spoken": "50 rojos",
        "vehicle_mentions": [VehicleMention(make="Toyota", model="Hilux", color="blanco", plate=None)],
        "trip_date": None,
        "notes": None,
        "confidence": 0.9,
    }
    values.update(overrides)
    return TripAudioExtraction(**values)


def make_ogg(seed: str = "nota") -> bytes:
    """Firma OGG válida; el contenido no importa porque la transcripción va simulada."""
    return b"OggS" + bytes([0, 2]) + seed.encode() * 40


class FakeTranscriber:
    model = "whisper-large-v3"

    def __init__(self, text: str = "Salí del Coyol a la Uruca con una Hilux blanca, fueron 50 rojos", duration: float = 42.0):
        self.text = text
        self.duration = duration
        self.calls: list[dict] = []

    def transcribe(self, data, filename, media_type, prompt):
        self.calls.append({"filename": filename, "media_type": media_type, "prompt": prompt})
        return Transcription(text=self.text, duration_seconds=self.duration, model=self.model)


class FailingTranscriber(FakeTranscriber):
    def transcribe(self, data, filename, media_type, prompt):
        from app.services.transcription_service import TranscriptionError

        raise TranscriptionError("El servicio de transcripción respondió con error 503")


def post_photo(client, data, filename="vin.jpg", content_type="image/jpeg", **form):
    return client.post("/intake/vin-photo", files={"file": (filename, data, content_type)}, data=form)


def post_audio(client, data, filename="nota.ogg", content_type="audio/ogg", **form):
    return client.post("/intake/audio", files={"file": (filename, data, content_type)}, data=form)


class Api:
    """App con base desechable, Storage en memoria, Claude/NHTSA/transcripción
    simulados y el usuario que se elija (los permisos se revisan de verdad)."""

    def __init__(self, db, monkeypatch):
        from fastapi.testclient import TestClient

        from app.api import intake as intake_api
        from app.api.deps import get_current_user_claims
        from app.database.session import get_db
        from app.main import app
        from app.schemas.intake import NhtsaDecodeOut
        from app.services import nhtsa_service

        self.db = db
        self.fleet = seed_fleet(db)
        self.storage = FakeStorage()
        self.extractor = FakeExtractor(make_extraction(), trip_readings=[self.trip_extraction()])
        self.transcriber = FakeTranscriber()
        self.user_id = self.fleet.driver_user_id
        self.nhtsa_calls: list[str] = []

        def fake_decode(vin):
            self.nhtsa_calls.append(vin)
            return NhtsaDecodeOut(make="HONDA", model="Accord", model_year=2003, error_code="0")

        monkeypatch.setattr(nhtsa_service, "decode_vin", fake_decode)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user_claims] = lambda: {"sub": self.user_id}
        app.dependency_overrides[intake_api.get_extractor] = lambda: self.extractor
        app.dependency_overrides[intake_api.get_storage] = lambda: self.storage
        app.dependency_overrides[intake_api.get_transcriber] = lambda: self.transcriber
        self.client = TestClient(app)

    def trip_extraction(self, **overrides):
        """Extracción que nombra las zonas reales del viaje sembrado."""
        values = {
            "origin": place("el Coyol", "El Coyol, Alajuela", self.fleet.origin.name),
            "destination": place("la Uruca", "La Uruca, San José", self.fleet.destination.name),
        }
        values.update(overrides)
        return make_trip_extraction(**values)

    def as_user(self, user_id):
        self.user_id = user_id
        return self

    def photo(self, data=None, trip=True):
        form = {"trip_id": str(self.fleet.trip.id)} if trip else {}
        return post_photo(self.client, data if data is not None else make_jpeg(), **form)

    def audio(self, data=None, trip=True):
        form = {"trip_id": str(self.fleet.trip.id)} if trip else {}
        return post_audio(self.client, data if data is not None else make_ogg(), **form)
