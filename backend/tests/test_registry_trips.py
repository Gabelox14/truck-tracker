"""Viajes del registro histórico de terceros sin cuenta ("JP", "MYR"): sin chofer
ni camión, con la unidad tal como la escribe el registro."""

from app.models import Trip
from app.services import trip_service


def test_trip_without_driver_shows_its_unit(api):
    fleet = api.fleet
    api.db.add(
        Trip(
            driver_id=None,
            truck_id=None,
            unit_label="JP",
            origin_zone_id=fleet.origin.id,
            destination_zone_id=fleet.destination.id,
            trip_type="directo",
            status="completed",
            amount=50000,
        )
    )
    api.db.flush()

    directos = trip_service.build_directos_rows(api.db)
    assert "JP" in {row["unit"] for row in directos}

    client = api.as_user(fleet.admin_id).client
    fe = [r for r in client.get("/trips/export/fe/preview").json() if r["truck_code"] == "JP"]
    assert fe and fe[0]["driver_name"] is None
    listed = [t for t in client.get("/trips").json() if t["unit_label"] == "JP"]
    assert listed and listed[0]["driver_id"] is None
    assert client.get("/trips/stats/summary").status_code == 200
    # Un chofer no ve viajes ajenos sin chofer.
    mine = api.as_user(fleet.driver_user_id).client.get("/trips").json()
    assert all(t["unit_label"] is None for t in mine)
