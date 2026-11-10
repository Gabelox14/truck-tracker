"""Proyección del mes siguiente y "dónde se pierde plata". Datos sintéticos con la forma del
registro real: viajes completados, con carros y monto, entre zonas con distancia."""

from datetime import date, datetime, time

import pytest

from app.core.time import COSTA_RICA_TZ
from app.models import Trip, TripCar, Truck, Zone, ZoneDistance
from app.services import insights_service

TODAY = date(2026, 5, 15)


@pytest.fixture
def world(db):
    zones = {name: Zone(name=f"{name} ins") for name in ("Base", "Centro", "Lejos")}
    db.add_all(zones.values())
    trucks = {
        "C1": Truck(plate="INS-C1", code="C1", body_type="Cabezal o tracto camión"),
        "P1": Truck(plate="INS-P1", code="P1", body_type="Plataforma"),
        "N1": Truck(plate="INS-N1", code="N1", body_type="Plataforma"),
    }
    db.add_all(trucks.values())
    db.flush()
    for a, b, km in (("Base", "Centro", 20), ("Base", "Lejos", 150), ("Centro", "Lejos", 140)):
        first, second = sorted((zones[a].id, zones[b].id), key=str)
        db.add(ZoneDistance(zone_a_id=first, zone_b_id=second, km=km))
    db.flush()

    def trip(truck, day, origin, destination, cars, per_car, notes=None, review="ok"):
        moment = datetime.combine(day, time(12), tzinfo=COSTA_RICA_TZ)
        t = Trip(
            truck_id=trucks[truck].id, origin_zone_id=zones[origin].id, destination_zone_id=zones[destination].id,
            status="completed", started_at=moment, completed_at=moment, amount=cars * per_car,
            trip_type="directo", review_status=review, review_notes=notes,
        )
        db.add(t)
        db.flush()
        db.add_all(TripCar(trip_id=t.id, brand="Suzuki", amount=per_car) for _ in range(cars))
        return t

    return trip


def fill_months(trip):
    # Ene, feb y mar completos; abril casi vacío (registro incompleto).
    for month in (1, 2, 3):
        for day in range(1, 11):
            trip("C1", date(2026, month, day), "Base", "Centro", 3, 50_000)
            trip("P1", date(2026, month, day), "Base", "Centro", 1, 45_000)
        trip("C1", date(2026, month, 20), "Base", "Centro", 1, 50_000)  # salió casi vacío
        trip("P1", date(2026, month, 21), "Base", "Lejos", 1, 60_000)  # ruta larga que paga poco
    trip("P1", date(2026, 4, 2), "Base", "Centro", 1, 45_000)


def test_forecast_uses_the_last_normal_months_and_sums_each_truck(db, world):
    fill_months(world)
    # N1 empezó en marzo: promedia solo ese mes, no se diluye entre tres.
    for day in range(1, 6):
        world("N1", date(2026, 3, day), "Centro", "Base", 1, 40_000)
    world("P1", date(2025, 6, 3), "Base", "Centro", 1, 45_000)  # junio del año pasado

    result = insights_service.build_forecast(db, TODAY)

    assert result["target_month"] == "2026-06"
    assert result["basis_months"] == ["2026-01", "2026-02", "2026-03"]  # abril queda fuera: incompleto
    history = {h["month"]: h for h in result["history"]}
    assert history["2026-04"]["normal"] is False and history["2026-03"]["basis"] is True
    units = {u["unit"]: u for u in result["by_unit"]}
    assert units["C1"]["amount"] == 10 * 3 * 50_000 + 50_000
    assert (units["N1"]["months"], units["N1"]["amount"], units["N1"]["trips"]) == (1, 200_000, 5)
    assert result["fleet"]["amount"] == sum(u["amount"] for u in result["by_unit"])
    assert result["fleet"]["low"] <= result["fleet"]["amount"] <= result["fleet"]["high"]
    assert result["same_month_last_year"] == {"month": "2025-06", "amount": 45_000, "normal": False}
    assert result["current_month"]["trips"] == 0


def test_forecast_without_a_complete_month(db, world):
    result = insights_service.build_forecast(db, TODAY)
    assert result["fleet"] is None and result["by_unit"] == []


def test_insights_find_unused_capacity_empty_returns_and_low_paying_routes(db, world):
    fill_months(world)
    world("C1", date(2026, 2, 25), "Base", "Centro", 2, 25_000, notes="Rebote (registro)")
    world("P1", date(2026, 3, 25), "Base", "Centro", 1, 45_000, review="needs_review")

    result = insights_service.build_insights(db, TODAY)

    assert result["window_months"] == ["2026-01", "2026-02", "2026-03"]
    assert result["base_zone"] == "Base ins"
    assert result["km_coverage"] == 1

    capacity = {c["unit"]: c for c in result["capacity"]}
    assert set(capacity) == {"C1"}  # las plataformas suelen llevar uno: no tienen espacio "libre"
    assert capacity["C1"]["typical_load"] == 3
    assert capacity["C1"]["under_trips"] == 4  # 3 viajes de 1 carro + el rebote de 2
    assert capacity["C1"]["top_route"] == {"origin": "Base ins", "destination": "Centro ins", "trips": 4}
    assert capacity["C1"]["opportunity_per_month"] > 0

    legs = {(leg["origin"], leg["destination"]): leg for leg in result["empty_legs"]}
    assert ("Centro ins", "Base ins") in legs and ("Lejos ins", "Base ins") in legs

    routes = {(r["origin"], r["destination"]): r for r in result["routes"]}
    assert routes[("Base ins", "Centro ins")]["low_pay"] is False
    assert ("Base ins", "Lejos ins") not in routes  # menos de 5 viajes: no alcanza para juzgar

    units = {u["unit"]: u for u in result["units"]}
    assert units["C1"]["kind"] == "cabezal" and units["P1"]["kind"] == "plataforma"
    assert 0 < units["P1"]["empty_share"] < 1
    assert result["rebotes"]["trips"] == 1 and result["rebotes"]["amount"] == 50_000
    assert result["pending_review"] == {"trips": 1, "amount": 45_000}


def test_low_paying_route_is_flagged(db, world):
    fill_months(world)
    for day in range(11, 17):  # seis viajes largos a ₡60.000: ₡200 por km contra el promedio de la flota
        world("P1", date(2026, 3, day), "Base", "Lejos", 1, 60_000)
    routes = {(r["origin"], r["destination"]): r for r in insights_service.build_insights(db, TODAY)["routes"]}
    long_route = routes[("Base ins", "Lejos ins")]
    assert long_route["low_pay"] is True
    assert long_route["amount_per_km"] == pytest.approx(60_000 / 300, rel=0.01)


def test_days_without_distance_stay_out_of_the_km(db, world):
    fill_months(world)
    lonely = Zone(name="Sin distancia ins")
    db.add(lonely)
    db.flush()
    for day in range(11, 14):
        t = Trip(
            truck_id=db.query(Truck).filter_by(code="N1").one().id,
            origin_zone_id=db.query(Zone).filter_by(name="Base ins").one().id, destination_zone_id=lonely.id,
            status="completed", amount=50_000,
            started_at=datetime.combine(date(2026, 2, day), time(12), tzinfo=COSTA_RICA_TZ),
        )
        db.add(t)
    db.flush()
    result = insights_service.build_insights(db, TODAY)
    assert result["km_coverage"] < 1
    units = {u["unit"]: u for u in result["units"]}
    assert units["N1"]["km_per_month"] is None


def test_stats_endpoints_are_for_staff_only(api):
    admin = api.as_user(api.fleet.admin_id).client
    assert admin.get("/trips/stats/forecast").status_code == 200
    assert admin.get("/trips/stats/insights").status_code == 200
    driver = api.as_user(api.fleet.driver_user_id).client
    assert driver.get("/trips/stats/forecast").status_code == 403
    assert driver.get("/trips/stats/insights").status_code == 403
