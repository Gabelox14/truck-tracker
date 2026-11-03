from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TruckDetails(BaseModel):
    """Datos que solo maneja el admin (código interno y ficha del Registro)."""

    code: str | None = None
    brand: str | None = None
    model: str | None = None
    year: int | None = Field(default=None, ge=1950, le=2100)
    vin: str | None = None
    color: str | None = None
    body_type: str | None = None
    traction: str | None = None


class TruckCreate(TruckDetails):
    plate: str


class TruckUpdate(TruckDetails):
    plate: str | None = None


class TruckOut(TruckDetails):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plate: str
    created_at: datetime
