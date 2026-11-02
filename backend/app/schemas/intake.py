from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.trip import TripOut
from app.schemas.trip_car import TripCarOut

VinLocation = Literal["parabrisas", "puerta", "documento", "otro"]
ImageQuality = Literal["buena", "regular", "mala"]
ReviewStatus = Literal["ok", "needs_review", "confirmed"]


class VinBox(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class VinPhotoExtraction(BaseModel):
    """Lo que Claude lee en la foto; la respuesta del modelo se valida contra este esquema."""

    model_config = ConfigDict(protected_namespaces=())

    vin_text: str | None = Field(
        description=(
            "VIN o número de chasis tal como aparece impreso, carácter por carácter, "
            "con '?' en cada carácter que no se pueda leer con certeza. null si no hay ninguno visible."
        )
    )
    vin_location: VinLocation | None = Field(
        description="Dónde está el VIN: parabrisas, puerta (calcomanía del marco), documento u otro. null si no hay VIN."
    )
    make: str | None = Field(
        description="Marca del vehículo según lo que se ve (logo, calcomanía, documento). null si no se distingue."
    )
    model: str | None = Field(
        description="Modelo comercial sin versión ni equipamiento (p. ej. 'FRONX', no 'FRONX GL AT'). null si no se distingue."
    )
    model_year: int | None = Field(
        description="Año modelo solo si aparece escrito en la etiqueta o el documento. null si no aparece."
    )
    color: str | None = Field(description="Color principal en español. null si no se ve la carrocería.")
    image_quality: ImageQuality = Field(description="Calidad de la foto para leer el VIN.")
    confidence: float = Field(
        ge=0, le=1, description="Seguridad de 0 a 1 de que vin_text está bien leído. 0 si vin_text es null."
    )
    vin_image: int | None = Field(
        description="Número de la foto (1, 2...) en la que se ve el VIN. null si no hay VIN."
    )
    vin_bbox: VinBox | None = Field(
        description="Rectángulo que encierra el VIN, en píxeles de la foto indicada en vin_image. null si no hay VIN."
    )
    notes: str | None = Field(
        description="Observación breve en español (reflejos, borroso, VIN cortado). null si no hay nada que señalar."
    )


class NhtsaDecodeOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    make: str | None = None
    model: str | None = None
    model_year: int | None = None
    error_code: str | None = None
    error_text: str | None = None


class AiUsageOut(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    calls: int


class VinPhotoResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    vin_text: str | None
    vin_location: VinLocation | None
    make: str | None
    model: str | None
    color: str | None
    image_quality: ImageQuality
    confidence: float
    notes: str | None
    vin: str | None
    vin_valid: bool
    check_digit_ok: bool | None
    nhtsa: NhtsaDecodeOut | None
    wmi_make: str | None = None
    model_year: int | None = None
    make_matches: bool | None
    review_status: ReviewStatus
    review_reasons: list[str]
    usage: AiUsageOut


class VinPhotoIntakeOut(VinPhotoResult):
    """Resultado guardado: el archivo, el viaje y el carro creado (si hay viaje)."""

    intake_file_id: UUID
    trip_id: UUID | None = None
    trip_car_id: UUID | None = None
    duplicate: bool = False


class FileUrlOut(BaseModel):
    url: str
    expires_in: int


Currency = Literal["CRC", "USD"]


class PlaceExtraction(BaseModel):
    spoken: str = Field(description="El lugar tal como lo dijo el chofer.")
    normalized: str = Field(
        description="Nombre del lugar en Costa Rica bien escrito, con su provincia si se sabe (p. ej. 'Puerto Caldera, Puntarenas')."
    )
    zone: str | None = Field(
        description="Nombre exacto de una de las zonas de la empresa si el lugar es esa zona; null si no es ninguna."
    )


class VehicleMention(BaseModel):
    make: str | None = Field(description="Marca dicha, null si no se dijo.")
    model: str | None = Field(description="Modelo dicho, null si no se dijo.")
    color: str | None = Field(description="Color dicho, null si no se dijo.")
    plate: str | None = Field(description="Placa dicha, null si no se dijo.")


class TripAudioExtraction(BaseModel):
    """Lo que Claude extrae de la transcripción; la respuesta se valida contra este esquema."""

    origin: PlaceExtraction | None = Field(description="De dónde salió el viaje. null si no se dijo.")
    destination: PlaceExtraction | None = Field(description="A dónde llegó el viaje. null si no se dijo.")
    cost_amount: float | None = Field(
        ge=0, description="Costo del viaje en unidades de la moneda, ya convertida la jerga. null si no se dijo."
    )
    cost_currency: Currency | None = Field(
        description="CRC o USD según lo dicho. null si se dio un número sin decir la moneda."
    )
    cost_spoken: str | None = Field(description="La frase exacta del costo (p. ej. '50 rojos'). null si no se dijo.")
    cost_per_vehicle: bool | None = Field(
        description="true si el monto es por cada vehículo ('cada uno'), false si es el total del viaje, null si no se dijo monto."
    )
    plus_iva: bool | None = Field(description="true si dijo 'más IVA', false si dijo que lo incluye, null si no lo mencionó.")
    vehicle_count: int | None = Field(description="Cantidad de vehículos que dice que trasladó. null si no la dice.")
    unit_code: str | None = Field(description="La unidad (camión) tal como la dijo, p. ej. 'M2'. null si no la dijo.")
    driver_name: str | None = Field(description="Nombre del chofer si se menciona. null si no.")
    requested_by: str | None = Field(
        description="Nombre completo de quien solicitó el traslado ('lo solicita…', 'solicitado por…'). null si no se dice."
    )
    processed_by: str | None = Field(description="Con quién se tramita, si lo dice. null si no.")
    invoice_type: Literal["directa", "proforma"] | None = Field(
        description="'directa' si dice factura directa, 'proforma' si dice proforma, null si no lo dice."
    )
    in_contract: bool | None = Field(description="true si dice que está en contrato, false si dice que no, null si no lo dice.")
    vehicle_mentions: list[VehicleMention] = Field(description="Vehículos mencionados; lista vacía si ninguno.")
    trip_date: date | None = Field(description="Fecha del viaje si se menciona o se deduce (ayer, el lunes); null si no.")
    notes: str | None = Field(description="Otra información útil, breve y en español. null si no hay.")
    confidence: float = Field(ge=0, le=1, description="Seguridad de 0 a 1 en la extracción completa.")


class TranscriptionOut(BaseModel):
    model: str
    duration_seconds: float | None


class TripAudioResult(BaseModel):
    transcript: str
    extraction: TripAudioExtraction | None
    origin_zone_id: UUID | None
    destination_zone_id: UUID | None
    cost_amount: float | None
    cost_currency: Currency | None
    currency_assumed: bool = False
    cost_per_vehicle: bool | None = None
    rate_amount: float | None = None
    truck_id: UUID | None = None
    driver_id: UUID | None = None
    requested_by: str | None = None
    review_status: ReviewStatus
    review_reasons: list[str]
    transcription: TranscriptionOut
    usage: AiUsageOut | None


class IntakeFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    kind: Literal["vin_photo", "audio"]
    status: Literal["processed", "failed"]
    trip_id: UUID | None
    mime_type: str
    size_bytes: int
    transcript: str | None
    duration_seconds: float | None
    extraction: dict | None
    error: str | None
    ai_model: str | None
    input_tokens: int | None
    output_tokens: int | None
    created_by: UUID | None
    created_at: datetime


class AttachFileIn(BaseModel):
    trip_id: UUID


class DraftTripCreate(BaseModel):
    """Viaje creado por el staff a partir de borradores (fotos y/o audios sin viaje)."""

    file_ids: list[UUID] = Field(min_length=1)
    driver_id: UUID
    # Solo puede faltar si el chofer es tercero (vehículo propio).
    truck_id: UUID | None = None
    origin_zone_id: UUID
    destination_zone_id: UUID
    trip_type: Literal["directo", "indirecto"] | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: Currency = "CRC"
    trip_date: date | None = None
    requested_by: str | None = None
    completed: bool = True


class AudioIntakeOut(TripAudioResult):
    """Resultado guardado; trip_review_* refleja cómo quedó el viaje si se ligó a uno."""

    intake_file_id: UUID
    trip_id: UUID | None = None
    trip_review_status: ReviewStatus | None = None
    trip_review_reasons: list[str] = []
    duplicate: bool = False


class ReviewQueueOut(BaseModel):
    trips: list[TripOut]
    cars: list[TripCarOut]
    drafts: list[IntakeFileOut]
