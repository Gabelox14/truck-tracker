from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TruckCreate(BaseModel):
    plate: str
    code: str | None = None
    brand: str | None = None


class TruckUpdate(BaseModel):
    plate: str | None = None
    code: str | None = None
    brand: str | None = None


class TruckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plate: str
    code: str | None = None
    brand: str | None = None
    created_at: datetime
