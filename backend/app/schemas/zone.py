from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ZoneCreate(BaseModel):
    name: str


class ZoneUpdate(BaseModel):
    name: str


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
