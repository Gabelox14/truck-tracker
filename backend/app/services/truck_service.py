from sqlalchemy.orm import Session

from app.models.truck import Truck
from app.repositories import truck_repository


def list_trucks(db: Session, limit: int = 50, offset: int = 0) -> list[Truck]:
    return truck_repository.list_all(db, limit=limit, offset=offset)


def get_truck(db: Session, truck_id: str) -> Truck | None:
    return truck_repository.get(db, truck_id)


def create_truck(
    db: Session, plate: str, code: str | None = None, brand: str | None = None
) -> Truck:
    return truck_repository.create(db, plate, code=code, brand=brand)


def update_truck(
    db: Session,
    truck_id: str,
    plate: str | None = None,
    code: str | None = None,
    brand: str | None = None,
) -> Truck | None:
    return truck_repository.update(db, truck_id, plate=plate, code=code, brand=brand)


def delete_truck(db: Session, truck_id: str) -> bool:
    return truck_repository.delete(db, truck_id)
