from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.repositories import driver_repository


def list_drivers(db: Session, limit: int = 50, offset: int = 0) -> list[Driver]:
    return driver_repository.list_all(db, limit=limit, offset=offset)


def get_driver(db: Session, driver_id: str) -> Driver | None:
    return driver_repository.get(db, driver_id)


def create_driver(db: Session, profile_id: str, full_name: str) -> Driver:
    return driver_repository.create(db, profile_id, full_name)


def update_driver(
    db: Session, driver_id: str, full_name: str | None = None, active: bool | None = None
) -> Driver | None:
    return driver_repository.update(db, driver_id, full_name=full_name, active=active)


def delete_driver(db: Session, driver_id: str) -> bool:
    return driver_repository.delete(db, driver_id)
