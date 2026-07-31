from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DriverCreate(BaseModel):
    profile_id: UUID
    full_name: str


class DriverUpdate(BaseModel):
    full_name: str | None = None
    active: bool | None = None


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    full_name: str
    active: bool
    created_at: datetime
