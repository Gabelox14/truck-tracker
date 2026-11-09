from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.trip import TRIP_TYPES

Currency = Literal["CRC", "USD"]


class TripCreate(BaseModel):
    # El chofer con camión asignado sale siempre en ese camión; se ignora este campo.
    truck_id: UUID | None = None
    origin_zone_id: UUID
    destination_zone_id: UUID

    @model_validator(mode="after")
    def zones_must_differ(self) -> "TripCreate":
        if self.origin_zone_id == self.destination_zone_id:
            raise ValueError("origin_zone_id and destination_zone_id must differ")
        return self


class TripAmountUpdate(BaseModel):
    amount: float = Field(ge=0)
    currency: Currency | None = None


class TripTypeUpdate(BaseModel):
    trip_type: str

    @field_validator("trip_type")
    @classmethod
    def trip_type_must_be_valid(cls, v: str) -> str:
        if v not in TRIP_TYPES:
            raise ValueError(f"trip_type must be one of {TRIP_TYPES}")
        return v


class TripReviewUpdate(BaseModel):
    """Correcciones opcionales al confirmar lo extraído de un viaje."""

    amount: float | None = Field(default=None, ge=0)
    currency: Currency | None = None
    origin_zone_id: UUID | None = None
    destination_zone_id: UUID | None = None
    requested_by: str | None = None


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # Null: viaje del registro histórico de un tercero sin cuenta (ver unit_label).
    driver_id: UUID | None
    unit_label: str | None = None
    # Null: viaje de un tercero con su propio vehículo.
    truck_id: UUID | None
    origin_zone_id: UUID
    destination_zone_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    amount: float | None
    currency: Currency = "CRC"
    trip_type: str | None = None
    origin_text: str | None = None
    destination_text: str | None = None
    requested_by: str | None = None
    intake_source: str = "manual"
    review_status: str = "ok"
    review_notes: str | None = None
