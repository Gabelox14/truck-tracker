from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.trip import Trip

MAX_LIMIT = 200


def list_all(
    db: Session, driver_id: str | None = None, limit: int = 50, offset: int = 0
) -> list[Trip]:
    limit = min(limit, MAX_LIMIT)
    query = db.query(Trip)
    if driver_id is not None:
        query = query.filter(Trip.driver_id == driver_id)
    return query.order_by(Trip.started_at.desc()).limit(limit).offset(offset).all()


def get(db: Session, trip_id: str) -> Trip | None:
    return db.get(Trip, trip_id)


def list_all_unpaged(db: Session) -> list[Trip]:
    return db.query(Trip).order_by(Trip.started_at.desc()).all()


def create(
    db: Session, driver_id: str, truck_id: str, origin_zone_id: str, destination_zone_id: str
) -> Trip:
    trip = Trip(
        driver_id=driver_id,
        truck_id=truck_id,
        origin_zone_id=origin_zone_id,
        destination_zone_id=destination_zone_id,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def complete(db: Session, trip_id: str) -> Trip | None:
    trip = db.get(Trip, trip_id)
    if trip is None:
        return None
    trip.status = "completed"
    trip.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trip)
    return trip


def update_amount(db: Session, trip_id: str, amount: float) -> Trip | None:
    trip = db.get(Trip, trip_id)
    if trip is None:
        return None
    trip.amount = amount
    db.commit()
    db.refresh(trip)
    return trip
