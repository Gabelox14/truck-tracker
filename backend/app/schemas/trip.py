from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.trip import TRIP_TYPES


class TripCreate(BaseModel):
    truck_id: UUID
    origin_zone_id: UUID
    destination_zone_id: UUID

    @model_validator(mode="after")
    def zones_must_differ(self) -> "TripCreate":
        if self.origin_zone_id == self.destination_zone_id:
            raise ValueError("origin_zone_id and destination_zone_id must differ")
        return self


class TripAmountUpdate(BaseModel):
    amount: float


class TripTypeUpdate(BaseModel):
    trip_type: str

    @field_validator("trip_type")
    @classmethod
    def trip_type_must_be_valid(cls, v: str) -> str:
        if v not in TRIP_TYPES:
            raise ValueError(f"trip_type must be one of {TRIP_TYPES}")
        return v


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    driver_id: UUID
    truck_id: UUID
    origin_zone_id: UUID
    destination_zone_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    amount: float | None
    trip_type: str | None = None
