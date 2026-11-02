from sqlalchemy.orm import Session

from app.models.trip_car import TripCar


def list_for_trip(db: Session, trip_id: str) -> list[TripCar]:
    return db.query(TripCar).filter(TripCar.trip_id == trip_id).order_by(TripCar.created_at).all()


def list_needing_review(db: Session, limit: int = 200) -> list[TripCar]:
    return (
        db.query(TripCar)
        .filter(TripCar.review_status == "needs_review")
        .order_by(TripCar.created_at.desc())
        .limit(limit)
        .all()
    )


def get(db: Session, trip_id: str, car_id: str) -> TripCar | None:
    return db.query(TripCar).filter(TripCar.id == car_id, TripCar.trip_id == trip_id).first()


def get_by_photo(db: Session, photo_file_id: str) -> TripCar | None:
    return db.query(TripCar).filter(TripCar.photo_file_id == photo_file_id).first()


def create(db: Session, trip_id: str, fields: dict) -> TripCar:
    car = TripCar(trip_id=trip_id, **fields)
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


def add(db: Session, car: TripCar) -> TripCar:
    db.add(car)
    db.flush()
    return car


def update(db: Session, car: TripCar, fields: dict) -> TripCar:
    for key, value in fields.items():
        setattr(car, key, value)
    db.commit()
    db.refresh(car)
    return car


def delete(db: Session, trip_id: str, car_id: str) -> bool:
    car = get(db, trip_id, car_id)
    if car is None:
        return False
    db.delete(car)
    db.commit()
    return True
