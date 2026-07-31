from sqlalchemy.orm import Session

from app.models.trip_car import TripCar


def list_for_trip(db: Session, trip_id: str) -> list[TripCar]:
    return db.query(TripCar).filter(TripCar.trip_id == trip_id).order_by(TripCar.created_at).all()


def create(db: Session, trip_id: str, brand: str, vin_photo_url: str | None) -> TripCar:
    car = TripCar(trip_id=trip_id, brand=brand, vin_photo_url=vin_photo_url)
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


def delete(db: Session, trip_id: str, car_id: str) -> bool:
    car = (
        db.query(TripCar)
        .filter(TripCar.id == car_id, TripCar.trip_id == trip_id)
        .first()
    )
    if car is None:
        return False
    db.delete(car)
    db.commit()
    return True
