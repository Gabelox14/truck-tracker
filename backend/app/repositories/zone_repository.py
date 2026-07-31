from sqlalchemy.orm import Session

from app.models.zone import Zone

MAX_LIMIT = 200


def list_all(db: Session, limit: int = 50, offset: int = 0) -> list[Zone]:
    limit = min(limit, MAX_LIMIT)
    return db.query(Zone).order_by(Zone.name).limit(limit).offset(offset).all()


def get(db: Session, zone_id: str) -> Zone | None:
    return db.get(Zone, zone_id)


def create(db: Session, name: str) -> Zone:
    zone = Zone(name=name)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def update(db: Session, zone_id: str, name: str) -> Zone | None:
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None
    zone.name = name
    db.commit()
    db.refresh(zone)
    return zone


def delete(db: Session, zone_id: str) -> bool:
    zone = db.get(Zone, zone_id)
    if zone is None:
        return False
    db.delete(zone)
    db.commit()
    return True
