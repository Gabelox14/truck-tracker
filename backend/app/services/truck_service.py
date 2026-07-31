from sqlalchemy.orm import Session

from app.models.truck import Truck
from app.repositories import truck_repository


def list_trucks(db: Session, limit: int = 50, offset: int = 0) -> list[Truck]:
    return truck_repository.list_all(db, limit=limit, offset=offset)


def get_truck(db: Session, truck_id: str) -> Truck | None:
    return truck_repository.get(db, truck_id)


def create_truck(db: Session, plate: str) -> Truck:
    return truck_repository.create(db, plate)


def update_truck(db: Session, truck_id: str, plate: str) -> Truck | None:
    return truck_repository.update(db, truck_id, plate)


def delete_truck(db: Session, truck_id: str) -> bool:
    return truck_repository.delete(db, truck_id)
