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
    total_amount: float
    trip_count: int
    top_truck: StatsTruckOut | None = None
    by_day: list[StatsDayOut]
    by_truck: list[StatsTruckOut]
