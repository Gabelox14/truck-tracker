from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TripCarCreate(BaseModel):
    brand: str
    vin_photo_url: str | None = None


class TripCarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    brand: str
    vin_photo_url: str | None
    created_at: datetime
