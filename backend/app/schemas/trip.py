from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


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
