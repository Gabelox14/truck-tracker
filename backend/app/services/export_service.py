from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

TRIP_TYPE_LABEL = {"directo": "Directo", "indirecto": "Indirecto"}
MONEY_FORMAT = {"CRC": '"₡"#,##0.00', "USD": '"$"#,##0.00'}
DATE_FORMAT = "DD/MM/YYYY"

# (encabezado, ancho de columna)
FE_COLUMNS = [
    ("Fecha", 12),
    ("Viaje", 11),
    ("Código de Camión", 18),
    ("Placa", 12),
    ("Chofer", 22),
    ("Marca", 16),
    ("Modelo", 16),
    ("Año", 7),
    ("VIN", 21),
    ("VIN válido", 17),
    ("Origen", 18),
    ("Destino", 18),
    ("Tipo de Viaje", 14),
    ("Monto", 15),
    ("Moneda", 9),
    ("Estado", 12),
    ("Revisión", 13),
    ("Enlace", 10),
]
FE_HEADERS = [header for header, _ in FE_COLUMNS]
MONTO_COLUMN = FE_HEADERS.index("Monto") + 1
LINK_COLUMN = FE_HEADERS.index("Enlace") + 1


def _fe_sheet(ws, rows: list[dict]) -> None:
    ws.title = "FE"
    ws.append(FE_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows:
        amount = row.get("amount")
        ws.append(
            [
                row["trip_date"],
                str(row["trip_id"])[:8].upper(),
                row.get("truck_code") or "",
                row.get("truck_plate") or "",
                row.get("driver_name") or "",
                row.get("brand") or "",
                row.get("model") or "",
                row.get("model_year") or "",
                row.get("vin") or "",
                row.get("vin_status") or "",
                row.get("origin") or "",
                row.get("destination") or "",
                TRIP_TYPE_LABEL.get(row.get("trip_type"), ""),
                float(amount) if amount is not None else "",
                row.get("currency") if amount is not None else "",
                row.get("status") or "",
                row.get("review") or "",
                "Abrir",
            ]
        )
        line = ws.max_row
        ws.cell(row=line, column=1).number_format = DATE_FORMAT
        if amount is not None:
            ws.cell(row=line, column=MONTO_COLUMN).number_format = MONEY_FORMAT.get(row.get("currency"), MONEY_FORMAT["CRC"])
        link = ws.cell(row=line, column=LINK_COLUMN)
        link.hyperlink = row["link"]
        link.style = "Hyperlink"

    for i, (_, width) in enumerate(FE_COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(FE_COLUMNS))}{max(ws.max_row, 1)}"


def _period(summary: dict) -> str:
    date_from, date_to = summary.get("date_from"), summary.get("date_to")
    if not date_from and not date_to:
        return "Todos los viajes"
    start = date_from.strftime("%d/%m/%Y") if date_from else "el inicio"
    end = date_to.strftime("%d/%m/%Y") if date_to else "hoy"
    return f"{start} – {end}"


def _summary_sheet(ws, summary: dict) -> None:
    ws.title = "Resumen"
    ws.append(["Resumen"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append(["Periodo", _period(summary)])
    ws.append([])
    ws.append(["Moneda", "Viajes con monto", "Total"])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)
    for entry in summary["totals"]:
        ws.append([entry["currency"], entry["trips"], entry["total"]])
        ws.cell(row=ws.max_row, column=3).number_format = MONEY_FORMAT.get(entry["currency"], MONEY_FORMAT["CRC"])
    if not summary["totals"]:
        ws.append(["Sin montos en este periodo"])
    ws.append([])
    for label, key in (
        ("Viajes", "trip_count"),
        ("Vehículos", "vehicle_count"),
        ("Viajes sin monto", "trips_without_amount"),
        ("Viajes por revisar", "trips_needing_review"),
        ("Vehículos por revisar", "vehicles_needing_review"),
    ):
        ws.append([label, summary[key]])
    ws.append([])
    ws.append(["Cada viaje se cuenta una vez; en la hoja FE el monto del viaje se repite en cada vehículo."])
    ws.cell(row=ws.max_row, column=1).font = Font(italic=True, color="64748B")
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 18


def build_fe_workbook(rows: list[dict], summary: dict) -> BytesIO:
    wb = Workbook()
    _fe_sheet(wb.active, rows)
    _summary_sheet(wb.create_sheet(), summary)
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
