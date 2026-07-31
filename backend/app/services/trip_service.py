from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.profile import Profile
from app.models.trip import Trip
from app.models.trip_car import TripCar
from app.repositories import trip_car_repository, trip_repository, truck_repository, zone_repository


def create_trip(
    db: Session, driver_id: str, truck_id: str, origin_zone_id: str, destination_zone_id: str
) -> Trip:
    return trip_repository.create(db, driver_id, truck_id, origin_zone_id, destination_zone_id)


def complete_trip(db: Session, trip_id: str) -> Trip | None:
    return trip_repository.complete(db, trip_id)


def update_trip_amount(db: Session, trip_id: str, amount: float) -> Trip | None:
    return trip_repository.update_amount(db, trip_id, amount)


def list_trip_cars(db: Session, trip_id: str) -> list[TripCar]:
    return trip_car_repository.list_for_trip(db, trip_id)


def add_trip_car(db: Session, trip_id: str, brand: str, vin_photo_url: str | None) -> TripCar:
    return trip_car_repository.create(db, trip_id, brand, vin_photo_url)


def remove_trip_car(db: Session, trip_id: str, car_id: str) -> bool:
    return trip_car_repository.delete(db, trip_id, car_id)


def list_trips_for_user(db: Session, user_id: str, limit: int = 50, offset: int = 0) -> list[Trip]:
    profile = db.get(Profile, user_id)
    is_staff = profile is not None and profile.role in ("admin", "dispatcher")
    if is_staff:
        return trip_repository.list_all(db, limit=limit, offset=offset)

    driver = db.query(Driver).filter(Driver.profile_id == user_id).first()
    if driver is None:
        return []
    return trip_repository.list_all(db, driver_id=str(driver.id), limit=limit, offset=offset)


def build_fe_rows(db: Session) -> list[dict]:
    trips = trip_repository.list_all_unpaged(db)
    trucks = {t.id: t for t in truck_repository.list_all(db, limit=200)}
    zones = {z.id: z for z in zone_repository.list_all(db, limit=200)}

    rows = []
    for trip in trips:
        truck = trucks.get(trip.truck_id)
        zone_origin = zones.get(trip.origin_zone_id)
        zone_destination = zones.get(trip.destination_zone_id)
        base = {
            "truck_code": truck.code if truck else None,
            "truck_plate": truck.plate if truck else None,
            "origin": zone_origin.name if zone_origin else None,
            "destination": zone_destination.name if zone_destination else None,
            "amount": trip.amount,
        }
        cars = trip_car_repository.list_for_trip(db, str(trip.id))
        if cars:
            for car in cars:
                rows.append({**base, "brand": car.brand, "vin_photo_url": car.vin_photo_url})
        else:
            rows.append({**base, "brand": None, "vin_photo_url": None})
    return rows
