import io
import re
from collections import Counter, defaultdict

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.route_rate import RouteRate
from app.models.trip import Trip
from app.models.trip_car import TripCar
from app.models.zone import Zone
from app.repositories import trip_car_repository
from app.services import vin_service
from app.services.text_utils import fold

DEFAULT_CATEGORY = "directo"

# Modelos que se cobran como carga (más caros en la misma ruta). Sale del registro
# real de directos: los camiones JAC 1035 y 1042 pagan ₡10 000 más que un liviano;
# el JAC T6 (pickup) paga como liviano.
CARGO_MODELS = {"JAC": {"1035", "1042"}}

# Lugares que el registro escribe sin tildes.
_PLACE_NAMES = {"guapiles": "Guápiles", "perez zeledon": "Pérez Zeledón"}


class RateImportError(ValueError):
    pass


def vehicle_class_for(make: str | None, model: str | None) -> str:
    if make and model:
        make_key = vin_service.normalize_make(make)
        model_key = re.sub(r"[^A-Z0-9]", "", model.upper())
        model_key = model_key.removeprefix(re.sub(r"[^A-Z0-9]", "", make_key))
        if model_key in CARGO_MODELS.get(make_key, set()):
            return "carga"
    return "liviano"


def find_rate(db: Session, category: str, origin_zone_id, destination_zone_id, vehicle_class: str) -> RouteRate | None:
    """Tarifa de la ruta; si no está cargada en ese sentido, la del sentido contrario
    (en el registro real ambos sentidos cuestan lo mismo)."""
    for origin, destination in ((origin_zone_id, destination_zone_id), (destination_zone_id, origin_zone_id)):
        rate = (
            db.query(RouteRate)
            .filter(
                RouteRate.category == category,
                RouteRate.origin_zone_id == origin,
                RouteRate.destination_zone_id == destination,
                RouteRate.vehicle_class == vehicle_class,
            )
            .first()
        )
        if rate is not None:
            return rate
    return None


def rate_for_trip(db: Session, trip: Trip, vehicle_class: str = "liviano") -> RouteRate | None:
    rate = find_rate(
        db, trip.trip_type or DEFAULT_CATEGORY, trip.origin_zone_id, trip.destination_zone_id, vehicle_class
    )
    return rate if rate is not None and rate.currency == trip.currency else None


def price_car(db: Session, trip: Trip, car: TripCar) -> None:
    """Le pone al vehículo la tarifa de la ruta si todavía no tiene monto."""
    if car.amount is not None:
        return
    rate = rate_for_trip(db, trip, car.vehicle_class)
    if rate is not None:
        car.amount = rate.amount


def recompute_trip_amount(db: Session, trip: Trip) -> None:
    """Si los vehículos tienen monto, el monto del viaje es la suma."""
    db.flush()
    amounts = [car.amount for car in trip_car_repository.list_for_trip(db, str(trip.id)) if car.amount is not None]
    if amounts:
        trip.amount = sum(amounts)


def reprice_trip(db: Session, trip: Trip) -> None:
    """Vuelve a tarifar todos los vehículos (por ejemplo, si se corrigió la ruta)."""
    for car in trip_car_repository.list_for_trip(db, str(trip.id)):
        rate = rate_for_trip(db, trip, car.vehicle_class)
        if rate is not None:
            car.amount = rate.amount
    recompute_trip_amount(db, trip)


def list_rates(db: Session, category: str | None = None) -> list[RouteRate]:
    query = db.query(RouteRate)
    if category:
        query = query.filter(RouteRate.category == category)
    return query.all()


def _display_place(name: str) -> str:
    key = fold(name)
    return _PLACE_NAMES.get(key, " ".join(word.capitalize() for word in key.split()))


def _header_columns(rows) -> tuple[int, dict[str, int]]:
    for index, row in enumerate(rows):
        names = {fold(str(value)): col for col, value in enumerate(row) if value is not None}
        if {"ruta", "monto"} <= names.keys():
            return index, names
    raise RateImportError("No encontré las columnas RUTA y MONTO en la primera hoja")


def import_rates(db: Session, data: bytes, category: str = DEFAULT_CATEGORY) -> dict:
    """Arma las tarifas desde un registro facturado (una fila por vehículo con RUTA,
    VEHICULO y MONTO): por cada ruta y clase toma el monto que más se cobró."""
    try:
        sheet = load_workbook(io.BytesIO(data), data_only=True, read_only=True).worksheets[0]
    except Exception as exc:  # openpyxl lanza varios tipos según el archivo
        raise RateImportError("El archivo no es un Excel válido (.xlsx)") from exc
    rows = list(sheet.iter_rows(values_only=True))
    header_index, columns = _header_columns(rows[:15])
    route_col, amount_col = columns["ruta"], columns["monto"]
    vehicle_col = columns.get("vehiculo")

    seen: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    skipped: list[dict] = []
    rows_read = 0
    for row in rows[header_index + 1 :]:
        route = row[route_col] if route_col < len(row) else None
        amount = row[amount_col] if amount_col < len(row) else None
        if not route or amount in (None, ""):
            continue
        rows_read += 1
        route_text = " ".join(str(route).split())
        if "rebote" in fold(route_text):
            skipped.append({"route": route_text, "reason": "Rebote: pendiente de definir cómo se cobra"})
            continue
        parts = [part.strip() for part in re.split(r"\s+-\s+", route_text)]
        if len(parts) != 2 or not all(parts):
            skipped.append({"route": route_text, "reason": "No es una ruta 'ORIGEN - DESTINO'"})
            continue
        try:
            value = round(float(amount), 2)
        except (TypeError, ValueError):
            skipped.append({"route": route_text, "reason": f"Monto no numérico: {amount}"})
            continue
        vehicle = str(row[vehicle_col]).split() if vehicle_col is not None and row[vehicle_col] else []
        vehicle_class = vehicle_class_for(vehicle[0], " ".join(vehicle[1:])) if len(vehicle) > 1 else "liviano"
        seen[(fold(parts[0]), fold(parts[1]), vehicle_class)][value] += 1

    zones = {fold(zone.name): zone for zone in db.query(Zone).all()}
    zones_created: list[str] = []
    for origin, destination, _ in seen:
        for place in (origin, destination):
            if place not in zones:
                zone = Zone(name=_display_place(place))
                db.add(zone)
                db.flush()
                zones[place] = zone
                zones_created.append(zone.name)

    created = updated = 0
    conflicts: list[dict] = []
    for (origin, destination, vehicle_class), amounts in seen.items():
        (amount, times), *others = amounts.most_common()
        origin_zone, destination_zone = zones[origin], zones[destination]
        if others:
            conflicts.append(
                {
                    "route": f"{origin_zone.name} - {destination_zone.name}",
                    "vehicle_class": vehicle_class,
                    "chosen": amount,
                    "times": times,
                    "others": {str(value): count for value, count in others},
                }
            )
        rate = (
            db.query(RouteRate)
            .filter(
                RouteRate.category == category,
                RouteRate.origin_zone_id == origin_zone.id,
                RouteRate.destination_zone_id == destination_zone.id,
                RouteRate.vehicle_class == vehicle_class,
            )
            .first()
        )
        if rate is None:
            db.add(
                RouteRate(
                    category=category,
                    origin_zone_id=origin_zone.id,
                    destination_zone_id=destination_zone.id,
                    vehicle_class=vehicle_class,
                    amount=amount,
                    currency="CRC",
                )
            )
            created += 1
        elif float(rate.amount) != amount:
            rate.amount = amount
            updated += 1
    db.commit()
    return {
        "rows_read": rows_read,
        "rates_created": created,
        "rates_updated": updated,
        "zones_created": zones_created,
        "conflicts": conflicts,
        "skipped": skipped,
    }
