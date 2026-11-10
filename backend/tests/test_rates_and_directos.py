"""Tarifas por ruta, monto por vehículo, audio ampliado, varias fotos por vehículo
y el Excel "VINS DIRECTOS". Los datos son sintéticos con la forma del registro real."""

import io

from openpyxl import Workbook, load_workbook

from app.models import IntakeFile, RouteRate, Trip, TripCar, Zone
from app.services import export_service
from tests.helpers import make_extraction, make_jpeg


def register(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["FECHA", "VEHICULO", "VIN", "RUTA", "SOLICITADO", "CHOFER", "MONTO"])
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def route(api, origin=None, destination=None):
    return f"{(origin or api.fleet.origin.name).upper()} - {(destination or api.fleet.destination.name).upper()}"


def add_rate(api, amount, vehicle_class="liviano", origin=None, destination=None):
    payload = {
        "origin_zone_id": str(origin or api.fleet.origin.id),
        "destination_zone_id": str(destination or api.fleet.destination.id),
        "vehicle_class": vehicle_class,
        "amount": amount,
    }
    response = api.as_user(api.fleet.admin_id).client.post("/rates", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def upload_register(api, data):
    return api.client.post("/rates/import", files={"file": ("registro.xlsx", data, "application/vnd.ms-excel")})


# --- Tarifas -----------------------------------------------------------------


def test_import_builds_rates_from_billed_register(api):
    r = route(api)
    data = register(
        [
            ["2026-10-23", "SUZUKI JIMNY", "MA3JC74W1V0334920", r, "DAVID S", "M02", 45000],
            ["2026-10-23", "SUZUKI FRONX", "MBHWDB3S1VG905881", r, "DAVID S", "M02", 45000],
            ["2026-10-23", "SUZUKI SWIFT", "MBHZCEES7VG608337", r, "DAVID S", "M02", 45000],
            ["2026-10-24", "SUZUKI SPRESSO", "MA3FL61S2TA578231", r, "DAVID S", "M04", 50000],
            ["2026-10-24", "JAC 1042", "LJ11PBBC8V1301731", r, "BRYAN C", "M02", 55000],
            ["2026-10-24", "CHANGAN CS35", "LS4ASE2EXVB090226", route(api, destination="ZAPOTE"), "DAVID S", "M02", 55000],
            ["2026-10-14", "CHANGAN HONOR", "LS4ASE2E7VG800279", "GUAPILES - URUCA (REBOTE)", "KENNET S", "M03", 45000],
        ]
    )
    assert upload_register(api, data).status_code == 403  # solo admin

    summary = upload_register(api.as_user(api.fleet.admin_id), data).json()
    assert summary["rows_read"] == 7
    assert summary["rates_created"] == 3
    assert summary["zones_created"] == ["Zapote"]
    assert summary["conflicts"] == [
        {"route": f"{api.fleet.origin.name} - {api.fleet.destination.name}", "vehicle_class": "liviano",
         "chosen": 45000.0, "times": 3, "others": {"50000.0": 1}}
    ]
    assert summary["skipped"] == [
        {"route": "GUAPILES - URUCA (REBOTE)", "reason": "Rebote: pendiente de definir cómo se cobra", "count": 1}
    ]

    rates = {(rate["vehicle_class"], rate["amount"]) for rate in api.client.get("/rates").json()}
    assert rates == {("liviano", 45000.0), ("carga", 55000.0), ("liviano", 55000.0)}

    again = upload_register(api, data).json()
    assert (again["rates_created"], again["rates_updated"]) == (0, 0)


def test_rate_lookup_works_in_both_directions(api):
    add_rate(api, 45000)
    from app.services import rate_service

    reverse = rate_service.find_rate(api.db, "directo", api.fleet.destination.id, api.fleet.origin.id, "liviano")
    assert float(reverse.amount) == 45000


def test_admin_edits_and_deletes_rates(api):
    rate = add_rate(api, 45000)
    assert api.client.patch(f"/rates/{rate['id']}", json={"amount": 47000}).json()["amount"] == 47000
    assert api.as_user(api.fleet.driver_user_id).client.patch(f"/rates/{rate['id']}", json={"amount": 1}).status_code == 403
    assert api.as_user(api.fleet.admin_id).client.delete(f"/rates/{rate['id']}").status_code == 204
    assert api.db.query(RouteRate).count() == 0


# --- Monto por vehículo --------------------------------------------------------


def test_each_photographed_vehicle_takes_the_route_rate(api):
    add_rate(api, 45000)
    api.as_user(api.fleet.driver_user_id)
    first = api.db.get(TripCar, api.photo().json()["trip_car_id"])
    assert float(first.amount) == 45000
    assert float(api.db.get(Trip, api.fleet.trip.id).amount) == 45000
    api.photo(data=make_jpeg(color=(5, 5, 5)))
    assert float(api.db.get(Trip, api.fleet.trip.id).amount) == 90000


def test_cargo_vehicles_take_the_cargo_rate_and_totals_follow_changes(api):
    add_rate(api, 45000)
    add_rate(api, 55000, vehicle_class="carga")
    trip_id = api.fleet.trip.id
    car = api.client.post(f"/trips/{trip_id}/cars", json={"brand": "JAC", "model": "1042"}).json()
    assert (car["vehicle_class"], car["amount"]) == ("carga", 55000)
    api.client.post(f"/trips/{trip_id}/cars", json={"brand": "Suzuki", "model": "Jimny"})
    assert float(api.db.get(Trip, trip_id).amount) == 100000

    changed = api.client.patch(f"/trips/{trip_id}/cars/{car['id']}", json={"vehicle_class": "liviano"}).json()
    assert changed["amount"] == 45000
    assert float(api.db.get(Trip, trip_id).amount) == 90000
    api.client.delete(f"/trips/{trip_id}/cars/{car['id']}")
    assert float(api.db.get(Trip, trip_id).amount) == 45000


def test_correcting_the_route_reprices_the_vehicles(api):
    zapote = api.as_user(api.fleet.admin_id).client.post("/zones", json={"name": "Zapote"}).json()
    add_rate(api, 45000)
    add_rate(api, 55000, destination=zapote["id"])
    trip_id = api.fleet.trip.id
    car = api.client.post(f"/trips/{trip_id}/cars", json={"brand": "Suzuki", "model": "Fronx"}).json()
    assert car["amount"] == 45000
    api.client.patch(f"/trips/{trip_id}/review", json={"destination_zone_id": zapote["id"]})
    assert float(api.db.get(TripCar, car["id"]).amount) == 55000
    assert float(api.db.get(Trip, trip_id).amount) == 55000


# --- Nota de voz con unidad, solicitante y monto por vehículo -----------------


def note(api, **overrides):
    values = {
        "cost_amount": 45000,
        "cost_currency": "CRC",
        "cost_spoken": "45 mil colones más el IVA cada uno",
        "cost_per_vehicle": True,
        "plus_iva": True,
        "vehicle_count": 1,
        "unit_code": "M2",
        "driver_name": "Uno",
        "requested_by": "david sánchez",
        "invoice_type": "directa",
        "in_contract": True,
        "vehicle_mentions": [],
    }
    values.update(overrides)
    return api.trip_extraction(**values)


def test_note_fills_requester_category_and_prices_per_vehicle(api):
    add_rate(api, 45000)
    api.as_user(api.fleet.admin_id)
    api.photo()
    api.extractor.trip_readings = [note(api)]
    body = api.audio().json()
    assert body["trip_review_reasons"] == []
    trip = api.db.get(Trip, api.fleet.trip.id)
    assert trip.requested_by == "David Sánchez"
    assert trip.trip_type == "directo"
    assert float(trip.amount) == 45000


def test_note_that_disagrees_with_rate_unit_or_count_goes_to_review(api):
    add_rate(api, 45000)
    other = api.db.query(type(api.fleet.truck)).filter_by(id=api.fleet.truck.id).one()
    api.as_user(api.fleet.admin_id)
    api.photo()
    api.extractor.trip_readings = [note(api, cost_amount=50000, vehicle_count=2, unit_code="M5")]
    reasons = api.audio().json()["trip_review_reasons"]
    assert "El audio dice ₡50,000.00 por vehículo, pero la tarifa de esa ruta es ₡45,000.00" in reasons
    assert "El audio dice 2 vehículos, pero el viaje tiene 1" in reasons
    assert other.code == "M02"


def test_draft_note_prefills_truck_driver_requester_and_rate(api):
    add_rate(api, 45000)
    api.extractor.trip_readings = [note(api, cost_amount=None, cost_currency=None, cost_per_vehicle=None)]
    body = api.audio(trip=False).json()
    assert body["truck_id"] == str(api.fleet.truck.id)
    assert body["driver_id"] == str(api.fleet.driver.id)
    assert body["requested_by"] == "David Sánchez"
    assert (body["cost_amount"], body["cost_per_vehicle"], body["rate_amount"]) == (45000, True, 45000)
    assert "No se dijo el costo" not in body["review_reasons"]


def test_unknown_unit_is_flagged_on_drafts(api):
    api.extractor.trip_readings = [note(api, unit_code="M9")]
    assert "La unidad «M9» no está registrada como camión" in api.audio(trip=False).json()["review_reasons"]


# --- Varias fotos del mismo vehículo -------------------------------------------


def photos(api, *datas, trip=True):
    files = [("files", (f"foto{i}.jpg", data, "image/jpeg")) for i, data in enumerate(datas)]
    form = {"trip_id": str(api.fleet.trip.id)} if trip else {}
    return api.client.post("/intake/vin-photo", files=files, data=form)


def test_label_and_car_photos_make_one_vehicle(api):
    api.extractor.readings = [make_extraction(vin_image=1, model="FRONX")]
    response = photos(api, make_jpeg(color=(1, 1, 1)), make_jpeg(color=(2, 2, 2)))
    assert response.status_code == 200, response.text
    assert api.extractor.calls[0]["count"] == 2
    assert api.db.query(TripCar).filter(TripCar.trip_id == api.fleet.trip.id).count() == 1
    records = api.db.query(IntakeFile).all()
    primary = next(r for r in records if r.parent_id is None)
    extra = next(r for r in records if r.parent_id is not None)
    assert extra.parent_id == primary.id and extra.trip_id == api.fleet.trip.id
    assert len(api.storage.objects) == 2


def test_extra_photos_do_not_show_up_as_separate_drafts(api):
    photos(api, make_jpeg(color=(3, 3, 3)), make_jpeg(color=(4, 4, 4)), trip=False)
    queue = api.as_user(api.fleet.admin_id).client.get("/intake/review-queue").json()
    assert len(queue["drafts"]) == 1


def test_too_many_photos_for_one_vehicle(api):
    response = photos(api, *[make_jpeg(color=(i, i, i)) for i in range(5)])
    assert response.status_code == 400


# --- Excel "VINS DIRECTOS" -------------------------------------------------------


def test_directos_export_matches_the_manual_register(api):
    trip = api.db.get(Trip, api.fleet.trip.id)
    trip.trip_type = "directo"
    trip.requested_by = "David Sánchez"
    api.db.add(TripCar(trip_id=trip.id, brand="Suzuki", model="S-Presso", vin="MA3FL61SXTA573858", amount=45000))
    api.db.add(TripCar(trip_id=trip.id, brand="Suzuki", model="Fronx", vin="MBHWDB3S1VG905881", amount=45000))
    api.db.flush()

    response = api.as_user(api.fleet.admin_id).client.get("/trips/export/directos")
    assert response.status_code == 200
    ws = load_workbook(io.BytesIO(response.content))["Hoja1"]
    assert [cell.value for cell in ws[1]][:7] == ["FECHA", "VEHICULO", "VIN", "RUTA", "SOLICITADO", "CHOFER", "MONTO"]
    rows = [[cell.value for cell in row][1:7] for row in ws.iter_rows(min_row=2, max_row=3)]
    expected_route = f"{api.fleet.origin.name} - {api.fleet.destination.name}".upper()
    assert ["SUZUKI SPRESSO", "MA3FL61SXTA573858", expected_route, "DAVID S", "M02", 45000] in rows
    assert ["SUZUKI FRONX", "MBHWDB3S1VG905881", expected_route, "DAVID S", "M02", 45000] in rows
    assert ws["A2"].number_format == export_service.DIRECTOS_DATE_FORMAT
    assert ws["G2"].number_format == export_service.DIRECTOS_MONEY_FORMAT
    assert ws["H2"].value == "=SUM(G2:G3)"
    assert ws["I2"].value == "=H2*1.13"
    assert api.as_user(api.fleet.driver_user_id).client.get("/trips/export/directos").status_code == 403


def test_usados_register_adds_the_plate_after_the_vin(api):
    trip = api.db.get(Trip, api.fleet.trip.id)
    trip.trip_type, trip.fe_type = "directo", "directo_usado"
    api.db.add(TripCar(trip_id=trip.id, brand="Suzuki", model="Alto", vin="MA3FC62S4RA255838", plate="BZV824", amount=25000))
    api.db.flush()
    admin = api.as_user(api.fleet.admin_id).client

    response = admin.get("/trips/export/directos", params={"fe_type": "directo_usado"})
    assert response.status_code == 200
    assert "VINS USADOS DIRECTOS.xlsx" in response.headers["content-disposition"]
    ws = load_workbook(io.BytesIO(response.content))["Hoja1"]
    assert [cell.value for cell in ws[1]][:8] == ["FECHA", "VEHICULO", "VIN", "PLACA", "RUTA", "SOLICITADO", "CHOFER", "MONTO"]
    assert [ws["C2"].value, ws["D2"].value, ws["H2"].value] == ["MA3FC62S4RA255838", "BZV824", 25000]
    assert ws["I2"].value == "=SUM(H2:H2)"
    assert ws["J2"].value == "=I2*1.13"

    # Las proformas son otro registro: el viaje de usados no sale ahí.
    proformas = load_workbook(io.BytesIO(admin.get("/trips/export/directos", params={"fe_type": "proforma"}).content))
    assert proformas["Hoja1"]["A2"].value is None


def test_fe_shows_the_fe_type_and_plate_and_filters_by_it(api):
    trip = api.db.get(Trip, api.fleet.trip.id)
    trip.trip_type, trip.fe_type = "directo", "proforma"
    api.db.add(TripCar(trip_id=trip.id, brand="Suzuki", model="Vitara", vin="JS3TD04V4H4100051", plate="WDW-411"))
    api.db.flush()
    admin = api.as_user(api.fleet.admin_id).client

    rows = admin.get("/trips/export/fe/preview", params={"fe_type": "proforma"}).json()
    assert [(row["fe_type"], row["plate"]) for row in rows] == [("proforma", "WDW-411")]
    assert admin.get("/trips/export/fe/preview", params={"fe_type": "directo"}).json() == []
    assert admin.get("/trips/export/fe/preview", params={"fe_type": "otro"}).status_code == 422

    ws = load_workbook(io.BytesIO(admin.get("/trips/export/fe").content))["FE"]
    headers = [cell.value for cell in ws[1]]
    assert ws.cell(row=2, column=headers.index("Tipo de FE") + 1).value == "Proformas"
    assert ws.cell(row=2, column=headers.index("Placa del vehículo") + 1).value == "WDW-411"


def test_vehicle_plate_is_saved_normalized(api):
    admin = api.as_user(api.fleet.admin_id).client
    response = admin.post(
        f"/trips/{api.fleet.trip.id}/cars",
        json={"brand": "Suzuki", "model": "Alto", "vin": "MA3FC62S4RA255838", "plate": " bzv 824 "},
    )
    assert response.status_code == 201, response.text
    assert response.json()["plate"] == "BZV824"
    car_id = response.json()["id"]
    updated = admin.patch(f"/trips/{api.fleet.trip.id}/cars/{car_id}", json={"plate": "vch-007"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["plate"] == "VCH-007"


def test_trips_that_are_not_directos_stay_out(api):
    trip = api.db.get(Trip, api.fleet.trip.id)
    trip.trip_type = "indirecto"
    api.db.flush()
    ws = load_workbook(io.BytesIO(api.as_user(api.fleet.admin_id).client.get("/trips/export/directos").content))["Hoja1"]
    assert ws["A2"].value is None


def test_zone_names_import_with_accents(api):
    data = register([["2026-10-20", "SUZUKI FRONX", "MBHWDB3S4VG823529", route(api, destination="PEREZ ZELEDON"), "DAVID S", "M03", 205000]])
    summary = upload_register(api.as_user(api.fleet.admin_id), data).json()
    assert summary["zones_created"] == ["Pérez Zeledón"]
    assert api.db.query(Zone).filter(Zone.name == "Pérez Zeledón").count() == 1
