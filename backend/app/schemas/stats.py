from pydantic import BaseModel


class StatsDayOut(BaseModel):
    date: str
    total: float


class StatsTruckOut(BaseModel):
    truck_id: str
    plate: str
    code: str | None = None
    total: float


class StatsSummaryOut(BaseModel):
    currency: str = "CRC"
    totals_by_currency: dict[str, float] = {}
    pending_review: int = 0
    total_amount: float
    trip_count: int
    top_truck: StatsTruckOut | None = None
    by_day: list[StatsDayOut]
    by_truck: list[StatsTruckOut]
