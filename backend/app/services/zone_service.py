from sqlalchemy.orm import Session

from app.models.zone import Zone
from app.repositories import zone_repository


def list_zones(db: Session, limit: int = 50, offset: int = 0) -> list[Zone]:
    return zone_repository.list_all(db, limit=limit, offset=offset)


def get_zone(db: Session, zone_id: str) -> Zone | None:
    return zone_repository.get(db, zone_id)


def create_zone(db: Session, name: str) -> Zone:
    return zone_repository.create(db, name)


def update_zone(db: Session, zone_id: str, name: str) -> Zone | None:
    return zone_repository.update(db, zone_id, name)


def delete_zone(db: Session, zone_id: str) -> bool:
    return zone_repository.delete(db, zone_id)
