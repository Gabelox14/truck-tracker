"""Proyección del mes siguiente y dónde se pierde plata, a partir de los viajes registrados.

Solo colones (los dólares nunca se suman con colones). Los registros llegan con atraso y
hay meses incompletos, así que todo se calcula sobre "meses normales": los meses en que la
flota hizo al menos la mitad de los viajes de su mejor mes (el mismo criterio que usa el
análisis de rentabilidad de camiones_crawler).

Los km son aproximados: salen de la tabla zone_distances y de suponer que cada día de
trabajo arranca y termina en la zona base (el origen más frecuente). No hay GPS.
"""
from collections import Counter, defaultdict
from datetime import date
from statistics import median

from sqlalchemy.orm import Session

from app.core.time import costa_rica_today, local_date
from app.models.trip import Trip
from app.models.truck import Truck
from app.models.zone import Zone
from app.models.zone_distance import ZoneDistance
from app.repositories import trip_car_repository

CURRENCY = "CRC"
BASIS_MONTHS = 3  # meses normales que se promedian para proyectar
WORKING_DAYS = 22  # días hábiles de referencia en un mes
THIRD_PARTY = "Terceros"
MIN_ROUTE_TRIPS = 5  # una ruta entra en el análisis de plata por km con al menos estos viajes
LOW_PAY_RATIO = 0.6  # ruta que paga menos del 60 % del ₡/km de la flota


def _month(day: date) -> str:
    return day.strftime("%Y-%m")


def _next_month(month: str) -> str:
    year, number = int(month[:4]), int(month[5:7])
    return f"{year + number // 12}-{number % 12 + 1:02d}"


def _previous_year(month: str) -> str:
    return f"{int(month[:4]) - 1}{month[4:]}"


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _is_cabezal(truck: Truck | None, cars_per_trip: float) -> bool:
    if truck is not None and truck.body_type:
        return "cabezal" in truck.body_type.lower() or "tracto" in truck.body_type.lower()
    return cars_per_trip >= 2  # sin ficha: se deduce de cuántos carros lleva


class _Data:
    """Viajes en colones con sus vehículos, agrupados como los necesita el análisis."""

    def __init__(self, db: Session, today: date):
        self.today = today
        self.current_month = _month(today)
        trips = (
            db.query(Trip)
            .filter(Trip.currency == CURRENCY, Trip.status == "completed")
            .order_by(Trip.started_at)
            .all()
        )
        self.cars = trip_car_repository.by_trip(db, [trip.id for trip in trips])
        self.trucks = {truck.id: truck for truck in db.query(Truck).all()}
        self.zones = {zone.id: zone.name for zone in db.query(Zone).all()}
        self.distances = {
            frozenset((row.zone_a_id, row.zone_b_id)): float(row.km) for row in db.query(ZoneDistance).all()
        }
        self.trips = []
        for trip in trips:
            day = local_date(trip.started_at)
            cars = self.cars.get(trip.id, [])
            self.trips.append(
                {
                    "trip": trip,
                    "day": day,
                    "month": _month(day),
                    "unit": self.trucks[trip.truck_id].code or self.trucks[trip.truck_id].plate
                    if trip.truck_id in self.trucks
                    else THIRD_PARTY,
                    "cars": len(cars) or 1,
                    "car_amounts": [float(c.amount) for c in cars if c.amount is not None],
                    "amount": float(trip.amount or 0),
                }
            )
        history = defaultdict(lambda: {"trips": 0, "cars": 0, "amount": 0.0})
        for t in self.trips:
            if t["month"] < self.current_month:
                entry = history[t["month"]]
                entry["trips"] += 1
                entry["cars"] += t["cars"]
                entry["amount"] += t["amount"]
        self.history = dict(sorted(history.items()))
        best = max((m["trips"] for m in self.history.values()), default=0)
        self.normal_months = [m for m, v in self.history.items() if best and v["trips"] >= best / 2]
        self.basis = self.normal_months[-BASIS_MONTHS:]
        self.base_zone = Counter(t["trip"].origin_zone_id for t in self.trips).most_common(1)
        self.base_zone = self.base_zone[0][0] if self.base_zone else None

    def km(self, a, b) -> float | None:
        if a == b:
            return 0.0
        return self.distances.get(frozenset((a, b)))

    def first_month(self, unit: str) -> str | None:
        return next((t["month"] for t in self.trips if t["unit"] == unit), None)


def _month_totals(trips: list[dict]) -> dict:
    return {
        "trips": len(trips),
        "cars": sum(t["cars"] for t in trips),
        "amount": round(sum(t["amount"] for t in trips), 2),
    }


def build_forecast(db: Session, today: date | None = None) -> dict:
    data = _Data(db, today or costa_rica_today())
    target = _next_month(data.current_month)
    last_trip = max((t["day"] for t in data.trips), default=None)
    history = [
        {"month": m, **{k: (round(v, 2) if k == "amount" else v) for k, v in values.items()},
         "normal": m in data.normal_months, "basis": m in data.basis}
        for m, values in data.history.items()
    ][-12:]
    current = _month_totals([t for t in data.trips if t["month"] == data.current_month])
    result = {
        "currency": CURRENCY,
        "target_month": target,
        "basis_months": data.basis,
        "last_trip_date": last_trip,
        "current_month": {"month": data.current_month, **current},
        "history": history,
        "fleet": None,
        "same_month_last_year": None,
        "by_unit": [],
    }
    if not data.basis:
        return result

    last_year = _previous_year(target)
    if last_year in data.history:
        result["same_month_last_year"] = {
            "month": last_year,
            "amount": round(data.history[last_year]["amount"], 2),
            "normal": last_year in data.normal_months,
        }

    per_unit = defaultdict(lambda: defaultdict(list))
    for t in data.trips:
        if t["month"] in data.basis:
            per_unit[t["unit"]][t["month"]].append(t)
    rows = []
    for unit, months in per_unit.items():
        start = data.first_month(unit)
        # Un camión que arrancó a mitad de la base solo promedia los meses desde que trabaja.
        active = [m for m in data.basis if start and m >= start]
        totals = [_month_totals(months.get(m, [])) for m in active]
        rows.append(
            {
                "unit": unit,
                "months": len(active),
                "amount": round(_mean(x["amount"] for x in totals), 2),
                "low": round(min(x["amount"] for x in totals), 2),
                "high": round(max(x["amount"] for x in totals), 2),
                "trips": round(_mean(x["trips"] for x in totals), 1),
                "cars": round(_mean(x["cars"] for x in totals), 1),
            }
        )
    result["by_unit"] = sorted(rows, key=lambda r: -r["amount"])
    # La flota es la suma de cada camión: uno que arrancó a mitad de la base entra con su ritmo actual.
    # El rango es el peor y el mejor mes real de la flota en la base (sumar el peor mes de cada
    # camión daría un piso que nunca pasó).
    fleet_months = [data.history[m]["amount"] for m in data.basis]
    amount = sum(r["amount"] for r in rows)
    result["fleet"] = {
        "amount": round(amount, 2),
        "low": round(min(min(fleet_months), amount), 2),
        "high": round(max(max(fleet_months), amount), 2),
        "trips": round(sum(r["trips"] for r in rows)),
        "cars": round(sum(r["cars"] for r in rows)),
    }
    return result


def _day_km(data: _Data, trips: list[dict]) -> tuple[float, float, list] | None:
    """Km cargados y vacíos de un día de un camión, y sus tramos vacíos.
    Sale del origen más cercano a donde está; arranca y termina en la base."""
    position, loaded, empty, legs, left = data.base_zone, 0.0, 0.0, [], list(trips)
    while left:
        left.sort(key=lambda t: data.km(position, t["trip"].origin_zone_id) or 0)
        t = left.pop(0)
        to_origin = data.km(position, t["trip"].origin_zone_id)
        route = data.km(t["trip"].origin_zone_id, t["trip"].destination_zone_id)
        if to_origin is None or route is None:
            return None
        if to_origin:
            empty += to_origin
            legs.append((position, t["trip"].origin_zone_id, to_origin))
        loaded += route
        position = t["trip"].destination_zone_id
    back = data.km(position, data.base_zone)
    if back is None:
        return None
    if back:
        empty += back
        legs.append((position, data.base_zone, back))
    return loaded, empty, legs


def build_insights(db: Session, today: date | None = None) -> dict:
    data = _Data(db, today or costa_rica_today())
    window = data.basis
    result = {
        "currency": CURRENCY,
        "window_months": window,
        "base_zone": data.zones.get(data.base_zone),
        "units": [],
        "capacity": [],
        "routes": [],
        "fleet_amount_per_km": None,
        "empty_legs": [],
        "rebotes": {"trips": 0, "amount": 0.0},
        "pending_review": {"trips": 0, "amount": 0.0},
        "km_coverage": None,
    }
    pending = [t for t in data.trips if t["trip"].review_status == "needs_review"]
    result["pending_review"] = {"trips": len(pending), "amount": round(sum(t["amount"] for t in pending), 2)}
    if not window:
        return result
    months = len(window)
    trips = [t for t in data.trips if t["month"] in window]
    zone = data.zones.get

    rebotes = [t for t in trips if "rebote" in (t["trip"].review_notes or "").lower()]
    result["rebotes"] = {
        "trips": len(rebotes),
        "amount": round(sum(t["amount"] for t in rebotes), 2),  # cobran la mitad: es lo que se dejó de cobrar
        "per_month": round(sum(t["amount"] for t in rebotes) / months, 2),
    }

    # Precio por vehículo de cada ruta en la ventana (para valorar un carro más).
    route_car_prices = defaultdict(list)
    for t in trips:
        key = (t["trip"].origin_zone_id, t["trip"].destination_zone_id)
        route_car_prices[key] += t["car_amounts"] or [t["amount"] / t["cars"]]

    # Km por camión y día.
    by_unit_day = defaultdict(list)
    for t in trips:
        if t["unit"] != THIRD_PARTY:
            by_unit_day[(t["unit"], t["day"])].append(t)
    unit_km = defaultdict(lambda: {"loaded": 0.0, "empty": 0.0, "days": 0, "days_with_km": 0, "amount_with_km": 0.0})
    empty_legs = defaultdict(lambda: {"count": 0, "km": 0.0})
    days_known = days_total = 0
    for (unit, _day), day_trips in by_unit_day.items():
        stats = unit_km[unit]
        stats["days"] += 1
        days_total += 1
        km = _day_km(data, day_trips)
        if km is None:
            continue
        days_known += 1
        loaded, empty, legs = km
        stats["loaded"] += loaded
        stats["empty"] += empty
        stats["days_with_km"] += 1
        stats["amount_with_km"] += sum(t["amount"] for t in day_trips)
        for a, b, leg_km in legs:
            if b == data.base_zone:  # el regreso a la base es el tramo que una carga de retorno evita
                empty_legs[(a, b)]["count"] += 1
                empty_legs[(a, b)]["km"] += leg_km
    result["km_coverage"] = round(days_known / days_total, 3) if days_total else None

    total_km = sum(s["loaded"] + s["empty"] for s in unit_km.values())
    total_amount_km = sum(s["amount_with_km"] for s in unit_km.values())
    fleet_per_km = total_amount_km / total_km if total_km else None
    result["fleet_amount_per_km"] = round(fleet_per_km, 1) if fleet_per_km else None

    units = []
    trips_by_unit = defaultdict(list)
    for t in trips:
        if t["unit"] != THIRD_PARTY:
            trips_by_unit[t["unit"]].append(t)
    trucks_by_code = {(truck.code or truck.plate): truck for truck in data.trucks.values()}
    for unit, unit_trips in trips_by_unit.items():
        start = data.first_month(unit)
        active = len([m for m in window if start and m >= start]) or 1
        cars = sum(t["cars"] for t in unit_trips)
        amount = sum(t["amount"] for t in unit_trips)
        km = unit_km[unit]
        km_total = km["loaded"] + km["empty"]
        cars_per_trip = cars / len(unit_trips)
        typical = int(median(t["cars"] for t in unit_trips))
        truck = trucks_by_code.get(unit)
        days_per_month = km["days"] / active
        amount_per_day = amount / km["days"] if km["days"] else 0.0
        units.append(
            {
                "unit": unit,
                "plate": truck.plate if truck else None,
                "kind": "cabezal" if _is_cabezal(truck, cars_per_trip) else "plataforma",
                "months": active,
                "trips_per_month": round(len(unit_trips) / active, 1),
                "cars_per_trip": round(cars_per_trip, 2),
                "typical_load": typical,
                "days_per_month": round(days_per_month, 1),
                "idle_days_per_month": round(max(WORKING_DAYS - days_per_month, 0), 1),
                "amount_per_day": round(amount_per_day, 2),
                "amount_per_month": round(amount / active, 2),
                "km_per_month": round(km_total / active) if km["days_with_km"] else None,
                "empty_share": round(km["empty"] / km_total, 3) if km_total else None,
                "amount_per_km": round(km["amount_with_km"] / km_total, 1) if km_total else None,
            }
        )

        # Capacidad sin usar: viajes con menos carros de los que el camión suele llevar.
        if typical >= 2:
            under = [t for t in unit_trips if t["cars"] < typical]
            if under:
                missing_value = 0.0
                routes = Counter()
                for t in under:
                    key = (t["trip"].origin_zone_id, t["trip"].destination_zone_id)
                    price = _mean(route_car_prices[key])
                    missing_value += (typical - t["cars"]) * price
                    routes[key] += 1
                (top_o, top_d), top_n = routes.most_common(1)[0]
                result["capacity"].append(
                    {
                        "unit": unit,
                        "typical_load": typical,
                        "under_trips": len(under),
                        "under_share": round(len(under) / len(unit_trips), 3),
                        "missing_cars": sum(typical - t["cars"] for t in under),
                        "opportunity_per_month": round(missing_value / active, 2),
                        "top_route": {"origin": zone(top_o), "destination": zone(top_d), "trips": top_n},
                    }
                )
    result["units"] = sorted(units, key=lambda u: -u["amount_per_month"])
    result["capacity"].sort(key=lambda c: -c["opportunity_per_month"])

    # Plata por km de cada ruta (ida cargado y vuelta vacío).
    route_trips = defaultdict(list)
    for t in trips:
        route_trips[(t["trip"].origin_zone_id, t["trip"].destination_zone_id)].append(t)
    routes = []
    for (o, d), rt in route_trips.items():
        distance = data.km(o, d)
        if len(rt) < MIN_ROUTE_TRIPS or not distance:
            continue
        per_trip = _mean(t["amount"] for t in rt)
        per_km = per_trip / (2 * distance)
        routes.append(
            {
                "origin": zone(o),
                "destination": zone(d),
                "km": distance,
                "trips": len(rt),
                "trips_per_month": round(len(rt) / months, 1),
                "cars_per_trip": round(_mean(t["cars"] for t in rt), 2),
                "amount_per_trip": round(per_trip, 2),
                "amount_per_km": round(per_km, 1),
                "low_pay": bool(fleet_per_km and per_km < LOW_PAY_RATIO * fleet_per_km),
            }
        )
    result["routes"] = sorted(routes, key=lambda r: r["amount_per_km"])

    result["empty_legs"] = sorted(
        (
            {
                "origin": zone(a),
                "destination": zone(b),
                "trips_per_month": round(v["count"] / months, 1),
                "km_per_month": round(v["km"] / months),
            }
            for (a, b), v in empty_legs.items()
        ),
        key=lambda leg: -leg["km_per_month"],
    )[:6]
    return result
