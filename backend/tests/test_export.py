import io
import uuid
from datetime import date, datetime, timezone

from openpyxl import load_workbook

from app.core.config import settings
from app.models import Trip
from app.services import export_service

TRIP_A, TRIP_B = uuid.uuid4(), uuid.uuid4()


def _row(**overrides):
    row = {
        "trip_id": TRIP_A,
        "trip_date": date(2026, 10, 30),
        "truck_code": "M00",
        "truck_plate": "BCD123",
        "driver_name": "Angel",
        "origin": "Coyol",
        "destination": "Uruca",
        "amount": 85000,
        "currency": "CRC",
        "trip_type": "directo",
        "status": "Completado",
        "brand": "Toyota",
        "model": "Hilux",
        "model_year": 2021,
        "vin": "1HGCM82633A004352",
        "vin_status": "Sí",
        "review": "OK",
        "has_photo": True,
        "link": f"https://app.test/viajes/{TRIP_A}",
    }
    row.update(overrides)
    return row


SUMMARY = {
    "date_from": date(2026, 10, 1),
    "date_to": date(2026, 10, 31),
    "trip_count": 2,
    "vehicle_count": 2,
    "totals": [{"currency": "CRC", "trips": 1, "total": 85000.0}, {"currency": "USD", "trips": 1, "total": 150.0}],
    "trips_without_amount": 0,
    "trips_needing_review": 1,
    "vehicles_needing_review": 0,
}


def _workbook(rows, summary=SUMMARY):
    return load_workbook(io.BytesIO(export_service.build_fe_workbook(rows, summary).getvalue()))


def test_fe_sheet_layout_formats_and_links():
    rows = [
        _row(),
        _row(trip_id=TRIP_B, amount=150, currency="USD", brand=None, model=None, model_year=None, vin=None,
             vin_status=None, review="Por revisar", link=f"https://app.test/viajes/{TRIP_B}"),
    ]
    wb = _workbook(rows)
    assert wb.sheetnames == ["FE", "Resumen"]
    ws = wb["FE"]
    assert [cell.value for cell in ws[1]] == export_service.FE_HEADERS
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref == "A1:T3"

    first = {header: ws.cell(row=2, column=i + 1) for i, header in enumerate(export_service.FE_HEADERS)}
    assert first["Fecha"].value.date() == date(2026, 10, 30)
    assert first["Fecha"].number_format == "DD/MM/YYYY"
    assert first["Viaje"].value == str(TRIP_A)[:8].upper()
    assert first["VIN"].value == "1HGCM82633A004352"
    assert first["VIN válido"].value == "Sí"
    assert first["Monto"].value == 85000
    assert first["Monto"].number_format == '"₡"#,##0.00'
    assert first["Moneda"].value == "CRC"
    assert first["Enlace"].hyperlink.target == f"https://app.test/viajes/{TRIP_A}"

    second_amount = ws.cell(row=3, column=export_service.MONTO_COLUMN)
    assert second_amount.number_format == '"$"#,##0.00'
    assert ws.cell(row=3, column=export_service.FE_HEADERS.index("Revisión") + 1).value == "Por revisar"


def test_summary_sheet_counts_each_trip_once_per_currency():
    ws = _workbook([_row()])["Resumen"]
    values = [[cell.value for cell in row] for row in ws.iter_rows()]
    assert ["Periodo", "01/10/2026 – 31/10/2026"] == values[1][:2]
    assert ["CRC", 1, 85000] == values[4][:3]
    assert ["USD", 1, 150] == values[5][:3]
    assert ws.cell(row=6, column=3).number_format == '"$"#,##0.00'
    flat = {row[0]: row[1] for row in values if row and row[0]}
    assert flat["Viajes"] == 2
    assert flat["Viajes por revisar"] == 1


def test_export_endpoint_and_preview(api, monkeypatch):
    monkeypatch.setattr(settings, "app_base_url", "https://flota.test")
    api.photo()
    api.as_user(api.fleet.admin_id)
    trip = api.db.get(Trip, api.fleet.trip.id)
    # 01:30 UTC del 31 = 30 de octubre en Costa Rica.
    trip.started_at = datetime(2026, 10, 31, 1, 30, tzinfo=timezone.utc)
    trip.amount, trip.currency = 150, "USD"
    api.db.flush()

    params = {"date_from": "2026-10-30", "date_to": "2026-10-30"}
    preview = api.client.get("/trips/export/fe/preview", params=params).json()
    assert len(preview) == 1
    row = preview[0]
    assert row["trip_date"] == "2026-10-30"
    assert row["link"] == f"https://flota.test/viajes/{trip.id}"
    assert (row["brand"], row["model"], row["model_year"]) == ("Honda", "Accord", 2003)
    assert row["vin_status"] == "Sí"
    assert row["currency"] == "USD"
    assert row["driver_name"] == "Chofer Uno"
    assert api.client.get("/trips/export/fe/preview", params={"date_from": "2026-10-31"}).json() == []

    response = api.client.get("/trips/export/fe", params=params)
    assert response.status_code == 200
    wb = load_workbook(io.BytesIO(response.content))
    resumen = {row[0].value: row[1].value for row in wb["Resumen"].iter_rows() if row[0].value}
    assert resumen["Viajes"] == 1 and resumen["Vehículos"] == 1
    assert wb["FE"].cell(row=2, column=export_service.MONTO_COLUMN).number_format == '"$"#,##0.00'

    assert api.as_user(api.fleet.driver_user_id).client.get("/trips/export/fe").status_code == 403
