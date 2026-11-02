from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

VehicleClass = Literal["liviano", "carga"]
Category = Literal["directo", "indirecto"]


class RouteRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: Category
    origin_zone_id: UUID
    destination_zone_id: UUID
    vehicle_class: VehicleClass
    amount: float
    currency: Literal["CRC", "USD"]
    updated_at: datetime


class RouteRateCreate(BaseModel):
    category: Category = "directo"
    origin_zone_id: UUID
    destination_zone_id: UUID
    vehicle_class: VehicleClass = "liviano"
    amount: float = Field(gt=0)
    currency: Literal["CRC", "USD"] = "CRC"

    @model_validator(mode="after")
    def zones_must_differ(self) -> "RouteRateCreate":
        if self.origin_zone_id == self.destination_zone_id:
            raise ValueError("El origen y el destino tienen que ser distintos")
        return self


class RouteRateUpdate(BaseModel):
    amount: float = Field(gt=0)


class RateConflictOut(BaseModel):
    route: str
    vehicle_class: VehicleClass
    chosen: float
    times: int
    others: dict[str, int]


class RateSkippedOut(BaseModel):
    route: str
    reason: str
    count: int = 1


class RateImportOut(BaseModel):
    rows_read: int
    rates_created: int
    rates_updated: int
    zones_created: list[str]
    conflicts: list[RateConflictOut]
    skipped: list[RateSkippedOut]
