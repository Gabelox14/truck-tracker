from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TripCarCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    brand: str = Field(min_length=1)
    vin: str | None = None
    plate: str | None = None
    model: str | None = None
    model_year: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = None
    vehicle_class: Literal["liviano", "carga"] | None = None
    amount: float | None = Field(default=None, ge=0)


class TripCarUpdate(BaseModel):
    """Corrección de un carro; review_status="confirmed" lo da por revisado."""

    model_config = ConfigDict(protected_namespaces=())

    brand: str | None = None
    vin: str | None = None
    plate: str | None = None
    model: str | None = None
    model_year: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = None
    vehicle_class: Literal["liviano", "carga"] | None = None
    amount: float | None = Field(default=None, ge=0)
    review_status: Literal["confirmed", "needs_review"] | None = None


class TripCarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    trip_id: UUID
    brand: str | None
    make_from_photo: str | None = None
    model: str | None = None
    model_year: int | None = None
    color: str | None = None
    vin: str | None = None
    vin_raw: str | None = None
    plate: str | None = None
    vin_valid: bool | None = None
    check_digit_ok: bool | None = None
    ocr_confidence: float | None = None
    amount: float | None = None
    vehicle_class: str = "liviano"
    photo_file_id: UUID | None = None
    review_status: str = "ok"
    review_notes: str | None = None
    # VIN malo o que no coincide con la marca: bloquea confirmar y completar.
    vin_problem: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
