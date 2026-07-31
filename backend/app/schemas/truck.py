from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TruckCreate(BaseModel):
    plate: str


class TruckUpdate(BaseModel):
    plate: str


class TruckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plate: str
    created_at: datetime
