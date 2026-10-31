from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    model: str | None = Field(description="Modelo del vehículo si se distingue. null si no.")
    color: str | None = Field(description="Color principal en español. null si no se ve la carrocería.")
    image_quality: ImageQuality = Field(description="Calidad de la foto para leer el VIN.")
    confidence: float = Field(
        ge=0, le=1, description="Seguridad de 0 a 1 de que vin_text está bien leído. 0 si vin_text es null."
    )
    vin_bbox: VinBox | None = Field(
        description="Rectángulo que encierra el VIN, en píxeles de esta imagen. null si no hay VIN."
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
    make_matches: bool | None
    review_status: ReviewStatus
    review_reasons: list[str]
    usage: AiUsageOut
