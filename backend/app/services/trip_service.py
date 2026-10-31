from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.profile import Profile
from app.models.trip import Trip
from app.models.trip_car import TripCar
from app.repositories import trip_car_repository, trip_repository, truck_repository, zone_repository
from app.schemas.trip import TripReviewUpdate
from app.schemas.trip_car import TripCarCreate, TripCarUpdate
from app.services import vin_service


def create_trip(
    db: Session, driver_id: str, truck_id: str, origin_zone_id: str, destination_zone_id: str
) -> Trip:
    return trip_repository.create(db, driver_id, truck_id, origin_zone_id, destination_zone_id)


def complete_trip(db: Session, trip_id: str) -> Trip | None:
    return trip_repository.complete(db, trip_id)


def update_trip_amount(db: Session, trip_id: str, amount: float, currency: str | None = None) -> Trip | None:
    return trip_repository.update_amount(db, trip_id, amount, currency)


def review_trip(db: Session, trip: Trip, payload: TripReviewUpdate) -> Trip:
    """Aplica las correcciones enviadas y deja el viaje confirmado."""
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(trip, key, value)
    if trip.origin_zone_id == trip.destination_zone_id:
        db.rollback()
        raise ValueError("El origen y el destino tienen que ser distintos")
    trip.review_status = "confirmed"
    db.commit()
    db.refresh(trip)
    return trip


def update_trip_type(db: Session, trip_id: str, trip_type: str) -> Trip | None:
    return trip_repository.update_trip_type(db, trip_id, trip_type)


def list_trip_cars(db: Session, trip_id: str) -> list[TripCar]:
    return trip_car_repository.list_for_trip(db, trip_id)


def vin_fields(raw: str | None) -> dict:
    if raw is None or not raw.strip():
        return {"vin": None, "vin_raw": None, "vin_valid": None, "check_digit_ok": None}
    check = vin_service.analyze(raw)
    return {
        "vin": check.normalized,
        "vin_raw": raw.strip(),
        "vin_valid": check.is_valid,
        "check_digit_ok": check.check_digit_ok,
    }


def add_trip_car(db: Session, trip_id: str, payload: TripCarCreate, user_id: str) -> TripCar:
    fields = {
        "brand": payload.brand.strip(),
        "model": payload.model,
        "model_year": payload.model_year,
        "color": payload.color,
        "created_by": user_id,
        **vin_fields(payload.vin),
    }
    return trip_car_repository.create(db, trip_id, fields)


def get_trip_car(db: Session, trip_id: str, car_id: str) -> TripCar | None:
    return trip_car_repository.get(db, trip_id, car_id)


def update_trip_car(db: Session, car: TripCar, payload: TripCarUpdate) -> TripCar:
    changes = payload.model_dump(exclude_unset=True)
    fields = {key: changes[key] for key in ("brand", "model", "model_year", "color") if key in changes}
    if "vin" in changes:
        fields.update(vin_fields(changes["vin"]))
    if changes.get("review_status"):
        fields["review_status"] = changes["review_status"]
    return trip_car_repository.update(db, car, fields)


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


def build_fe_rows(
    db: Session,
    truck_id: str | None = None,
    zone_id: str | None = None,
    date_from=None,
    date_to=None,
    trip_type: str | None = None,
) -> list[dict]:
    trips = trip_repository.list_for_export(
        db,
        truck_id=truck_id,
        zone_id=zone_id,
        date_from=date_from,
        date_to=date_to,
        trip_type=trip_type,
    )
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
            "trip_type": trip.trip_type,
        }
        cars = trip_car_repository.list_for_trip(db, str(trip.id))
        if cars:
            for car in cars:
                rows.append({**base, "brand": car.brand, "has_photo": car.photo_file_id is not None})
        else:
            rows.append({**base, "brand": None, "has_photo": False})
    return rows


def build_stats(db: Session, date_from=None, date_to=None, currency: str = "CRC") -> dict:
    """Montos de una sola moneda (colones y dólares nunca se suman); la cantidad
    de viajes cuenta todos los del rango."""
    trips = trip_repository.list_for_export(db, date_from=date_from, date_to=date_to)
    trucks = {t.id: t for t in truck_repository.list_all(db, limit=200)}

    totals_by_currency: dict[str, float] = {}
    for trip in trips:
        if trip.amount is not None:
            totals_by_currency[trip.currency] = totals_by_currency.get(trip.currency, 0.0) + float(trip.amount)

    total_amount = 0.0
    by_day: dict[str, float] = {}
    by_truck: dict[str, dict] = {}

    for trip in trips:
        if trip.currency != currency:
            continue
        amount = float(trip.amount) if trip.amount is not None else 0.0
        total_amount += amount

        day_key = trip.started_at.date().isoformat()
        by_day[day_key] = by_day.get(day_key, 0.0) + amount

        truck_key = str(trip.truck_id)
        if truck_key not in by_truck:
            truck = trucks.get(trip.truck_id)
            by_truck[truck_key] = {
                "truck_id": truck_key,
                "plate": truck.plate if truck else "?",
                "code": truck.code if truck else None,
                "total": 0.0,
            }
        by_truck[truck_key]["total"] += amount

    by_day_list = [{"date": d, "total": round(v, 2)} for d, v in sorted(by_day.items())]
    by_truck_list = sorted(
        ({**v, "total": round(v["total"], 2)} for v in by_truck.values()),
        key=lambda r: r["total"],
        reverse=True,
    )
    top_truck = by_truck_list[0] if by_truck_list and by_truck_list[0]["total"] > 0 else None

    return {
        "currency": currency,
        "totals_by_currency": {key: round(value, 2) for key, value in totals_by_currency.items()},
        "pending_review": sum(1 for trip in trips if trip.review_status == "needs_review"),
        "total_amount": round(total_amount, 2),
        "trip_count": len(trips),
        "top_truck": top_truck,
        "by_day": by_day_list,
        "by_truck": by_truck_list,
    }
