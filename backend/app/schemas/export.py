from pydantic import BaseModel


class FeRowOut(BaseModel):
    truck_code: str | None = None
    truck_plate: str | None = None
    origin: str | None = None
    destination: str | None = None
    amount: float | None = None
    brand: str | None = None
    vin_photo_url: str | None = None
