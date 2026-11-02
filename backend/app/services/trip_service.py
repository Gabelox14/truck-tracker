from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import local_date
from app.models.driver import Driver
from app.models.profile import Profile
from app.models.trip import Trip
from app.models.trip_car import TripCar
from app.repositories import trip_car_repository, trip_repository, truck_repository, zone_repository
from app.schemas.trip import TripReviewUpdate
from app.schemas.trip_car import TripCarCreate, TripCarUpdate
from app.services import rate_service, vin_service
from app.services.text_utils import short_name, strip_accents

# Lo que se muestra en lugar del camión en los viajes de un tercero.
THIRD_PARTY_LABEL = "Tercero"


def create_trip(
    db: Session, driver_id: str, truck_id: str | None, origin_zone_id: str, destination_zone_id: str
) -> Trip:
    return trip_repository.create(db, driver_id, truck_id, origin_zone_id, destination_zone_id)


def complete_trip(db: Session, trip_id: str) -> Trip | None:
    return trip_repository.complete(db, trip_id)


def update_trip_amount(db: Session, trip_id: str, amount: float, currency: str | None = None) -> Trip | None:
    return trip_repository.update_amount(db, trip_id, amount, currency)


def review_trip(db: Session, trip: Trip, payload: TripReviewUpdate) -> Trip:
    """Aplica las correcciones enviadas y deja el viaje confirmado. Si cambia la
    ruta, los vehículos se vuelven a tarifar con la tarifa de la ruta nueva."""
    route = (trip.origin_zone_id, trip.destination_zone_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(trip, key, value)
    if trip.origin_zone_id == trip.destination_zone_id:
        db.rollback()
        raise ValueError("El origen y el destino tienen que ser distintos")
    if (trip.origin_zone_id, trip.destination_zone_id) != route:
        rate_service.reprice_trip(db, trip)
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
    """Carro agregado a mano: sin monto explícito toma la tarifa de la ruta."""
    trip = trip_repository.get(db, trip_id)
    brand = payload.brand.strip()
    car = TripCar(
        trip_id=trip.id,
        brand=brand,
        model=payload.model,
        model_year=payload.model_year,
        color=payload.color,
        created_by=user_id,
        vehicle_class=payload.vehicle_class or rate_service.vehicle_class_for(brand, payload.model),
        amount=payload.amount,
        **vin_fields(payload.vin),
    )
    rate_service.price_car(db, trip, car)
    trip_car_repository.add(db, car)
    rate_service.recompute_trip_amount(db, trip)
    db.commit()
    db.refresh(car)
    return car


def get_trip_car(db: Session, trip_id: str, car_id: str) -> TripCar | None:
    return trip_car_repository.get(db, trip_id, car_id)


def update_trip_car(db: Session, car: TripCar, payload: TripCarUpdate) -> TripCar:
    changes = payload.model_dump(exclude_unset=True)
    fields = {
        key: changes[key]
        for key in ("brand", "model", "model_year", "color", "vehicle_class", "amount")
        if key in changes
    }
    if "vin" in changes:
        fields.update(vin_fields(changes["vin"]))
    if changes.get("review_status"):
        fields["review_status"] = changes["review_status"]
    trip = trip_repository.get(db, str(car.trip_id))
    if "vehicle_class" in fields and "amount" not in fields and fields["vehicle_class"] != car.vehicle_class:
        # Cambió la clase: se vuelve a tomar la tarifa de esa clase.
        car.vehicle_class = fields["vehicle_class"]
        car.amount = None
        rate_service.price_car(db, trip, car)
        fields["amount"] = car.amount
    for key, value in fields.items():
        setattr(car, key, value)
    rate_service.recompute_trip_amount(db, trip)
    db.commit()
    db.refresh(car)
    return car


def remove_trip_car(db: Session, trip_id: str, car_id: str) -> bool:
    removed = trip_car_repository.delete(db, trip_id, car_id)
    if removed:
        trip = trip_repository.get(db, trip_id)
        rate_service.recompute_trip_amount(db, trip)
        db.commit()
    return removed


def list_trips_for_user(db: Session, user_id: str, limit: int = 50, offset: int = 0) -> list[Trip]:
    profile = db.get(Profile, user_id)
    is_staff = profile is not None and profile.role in ("admin", "dispatcher")
    if is_staff:
        return trip_repository.list_all(db, limit=limit, offset=offset)

    driver = db.query(Driver).filter(Driver.profile_id == user_id).first()
    if driver is None:
        return []
    return trip_repository.list_all(db, driver_id=str(driver.id), limit=limit, offset=offset)


STATUS_LABEL = {"in_progress": "En curso", "completed": "Completado"}


def _vin_label(car: TripCar | None) -> str | None:
    if car is None or not car.vin:
        return None
    if not car.vin_valid:
        return "No"
    return "Sí" if car.check_digit_ok else "Dígito no cuadra"


def _review_label(trip: Trip, car: TripCar | None) -> str:
    statuses = {trip.review_status, car.review_status if car else "ok"}
    if "needs_review" in statuses:
        return "Por revisar"
    return "Confirmado" if "confirmed" in statuses else "OK"


def _export_trips(db: Session, truck_id, zone_id, date_from, date_to, trip_type) -> list[Trip]:
    return trip_repository.list_for_export(
        db,
        truck_id=truck_id,
        zone_id=zone_id,
        date_from=date_from,
        date_to=date_to,
        trip_type=trip_type,
    )


def build_fe_rows(
    db: Session,
    truck_id: str | None = None,
    zone_id: str | None = None,
    date_from=None,
    date_to=None,
    trip_type: str | None = None,
) -> list[dict]:
    """Una fila por vehículo (o una por viaje si no lleva). El monto es del
    viaje, así que se repite en cada vehículo; el resumen lo cuenta una vez."""
    trips = _export_trips(db, truck_id, zone_id, date_from, date_to, trip_type)
    trucks = {t.id: t for t in truck_repository.list_all(db, limit=200)}
    zones = {z.id: z for z in zone_repository.list_all(db, limit=200)}
    drivers = {d.id: d for d in db.query(Driver).all()}
    base_url = settings.resolved_app_base_url

    rows = []
    for trip in trips:
        truck = trucks.get(trip.truck_id)
        zone_origin = zones.get(trip.origin_zone_id)
        zone_destination = zones.get(trip.destination_zone_id)
        driver = drivers.get(trip.driver_id)
        base = {
            "trip_id": trip.id,
            "trip_date": local_date(trip.started_at),
            "truck_code": truck.code if truck else None,
            "truck_plate": truck.plate if truck else (THIRD_PARTY_LABEL if trip.truck_id is None else None),
            "driver_name": driver.full_name if driver else None,
            "origin": zone_origin.name if zone_origin else None,
            "destination": zone_destination.name if zone_destination else None,
            "amount": trip.amount,
            "currency": trip.currency,
            "trip_type": trip.trip_type,
            "status": STATUS_LABEL.get(trip.status, trip.status),
            "link": f"{base_url}/viajes/{trip.id}",
        }
        cars = trip_car_repository.list_for_trip(db, str(trip.id)) or [None]
        for car in cars:
            rows.append(
                {
                    **base,
                    "brand": (car.brand or car.make_from_photo) if car else None,
                    "model": car.model if car else None,
                    "model_year": car.model_year if car else None,
                    "vin": car.vin if car else None,
                    "vin_status": _vin_label(car),
                    "review": _review_label(trip, car),
                    "has_photo": bool(car and car.photo_file_id),
                    # Con monto por vehículo, cada fila lleva el suyo; si no, el del viaje.
                    "amount": car.amount if car is not None and car.amount is not None else trip.amount,
                }
            )
    return rows


def _vehicle_label(car: TripCar) -> str:
    """'SUZUKI FRONX', 'SUZUKI SPRESSO', 'JAC 1042': como se escribe en el registro de directos."""
    parts = [car.brand or car.make_from_photo, car.model]
    return strip_accents(" ".join(part for part in parts if part)).upper().replace("-", "")


def build_directos_rows(db: Session, truck_id=None, zone_id=None, date_from=None, date_to=None) -> list[dict]:
    """Filas del registro "VINS DIRECTOS": una por vehículo de los viajes directos,
    en orden de fecha, con el monto de cada vehículo."""
    trips = sorted(
        _export_trips(db, truck_id, zone_id, date_from, date_to, "directo"),
        key=lambda trip: trip.started_at,
    )
    trucks = {t.id: t for t in truck_repository.list_all(db, limit=200)}
    zones = {z.id: z for z in zone_repository.list_all(db, limit=200)}
    rows = []
    for trip in trips:
        truck = trucks.get(trip.truck_id)
        origin, destination = zones.get(trip.origin_zone_id), zones.get(trip.destination_zone_id)
        base = {
            "trip_date": local_date(trip.started_at),
            "route": strip_accents(
                f"{origin.name if origin else '?'} - {destination.name if destination else '?'}"
            ).upper(),
            "requested_by": short_name(trip.requested_by),
            "unit": (truck.code or truck.plate) if truck else (THIRD_PARTY_LABEL.upper() if trip.truck_id is None else None),
        }
        cars = trip_car_repository.list_for_trip(db, str(trip.id))
        if not cars:
            rows.append({**base, "vehicle": None, "vin": None, "amount": trip.amount})
        for car in cars:
            amount = car.amount if car.amount is not None else (trip.amount if len(cars) == 1 else None)
            rows.append({**base, "vehicle": _vehicle_label(car), "vin": car.vin, "amount": amount})
    return rows


def build_fe_summary(
    db: Session,
    truck_id: str | None = None,
    zone_id: str | None = None,
    date_from=None,
    date_to=None,
    trip_type: str | None = None,
) -> dict:
    trips = _export_trips(db, truck_id, zone_id, date_from, date_to, trip_type)
    totals: dict[str, dict] = {}
    vehicle_count = vehicles_needing_review = 0
    for trip in trips:
        if trip.amount is not None:
            entry = totals.setdefault(trip.currency, {"currency": trip.currency, "trips": 0, "total": 0.0})
            entry["trips"] += 1
            entry["total"] += float(trip.amount)
        cars = trip_car_repository.list_for_trip(db, str(trip.id))
        vehicle_count += len(cars)
        vehicles_needing_review += sum(1 for car in cars if car.review_status == "needs_review")
    return {
        "date_from": date_from,
        "date_to": date_to,
        "trip_count": len(trips),
        "vehicle_count": vehicle_count,
        "totals": [
            {**entry, "total": round(entry["total"], 2)}
            for entry in sorted(totals.values(), key=lambda e: e["currency"])
        ],
        "trips_without_amount": sum(1 for trip in trips if trip.amount is None),
        "trips_needing_review": sum(1 for trip in trips if trip.review_status == "needs_review"),
        "vehicles_needing_review": vehicles_needing_review,
    }


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

        day_key = local_date(trip.started_at).isoformat()
        by_day[day_key] = by_day.get(day_key, 0.0) + amount

        if trip.truck_id is None:
            continue  # viaje de un tercero: suma al total, no a un camión
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
