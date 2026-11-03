from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FeRowOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    trip_id: UUID
    trip_date: date
    truck_code: str | None = None
    truck_plate: str | None = None
    driver_name: str | None = None
    origin: str | None = None
    destination: str | None = None
    amount: float | None = None
    currency: str = "CRC"
    trip_type: str | None = None
    status: str
    brand: str | None = None
    model: str | None = None
    model_year: int | None = None
    vin: str | None = None
    vin_status: str | None = None
    # VIN malo o que no coincide con la marca: el viaje no se puede completar.
    vin_problem: str | None = None
    review: str
    has_photo: bool = False
    link: str
