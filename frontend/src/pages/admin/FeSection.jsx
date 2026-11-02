import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { apiClient } from "../../lib/apiClient";
import { formatMoney } from "../../lib/formatMoney";
import { Badge, Button, Card, EmptyState, ErrorText, Select } from "../../components/ui";
import { useToast } from "../../context/ToastContext";

function useOptions(queryKey, path) {
  const { data } = useQuery({
    queryKey,
    queryFn: async () => (await apiClient.get(path)).data,
  });
  return data ?? [];
}

const TRIP_TYPE_LABEL = { directo: "Directo", indirecto: "Indirecto" };

function buildParams({ truckId, zoneId, dateFrom, dateTo, tripType }) {
  const params = {};
  if (truckId) params.truck_id = truckId;
  if (zoneId) params.zone_id = zoneId;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;
  if (tripType) params.trip_type = tripType;
  return params;
}

export default function FeSection() {
  const { showToast } = useToast();
  const [truckId, setTruckId] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [tripType, setTripType] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  const trucks = useOptions(["trucks"], "/trucks");
  const zones = useOptions(["zones"], "/zones");

  const filters = { truckId, zoneId, dateFrom, dateTo, tripType };
  const { data: rows, isLoading } = useQuery({
    queryKey: ["fe-preview", filters],
    queryFn: async () =>
      (await apiClient.get("/trips/export/fe/preview", { params: buildParams(filters) })).data,
  });

  function clearFilters() {
    setTruckId("");
    setZoneId("");
    setDateFrom("");
    setDateTo("");
    setTripType("");
  }

  async function handleDownload(kind = "fe") {
    setError("");
    setDownloading(kind);
    try {
      // El formato Directos solo incluye viajes directos: el filtro de tipo no aplica.
      const params = buildParams(kind === "directos" ? { ...filters, tripType: "" } : filters);
      const response = await apiClient.get(`/trips/export/${kind}`, { params, responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = kind === "directos" ? "VINS DIRECTOS.xlsx" : "FE.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showToast("Descarga iniciada");
    } catch {
      setError("No se pudo generar el archivo. Intentá de nuevo.");
    } finally {
      setDownloading(false);
    }
  }

  const hasFilters = truckId || zoneId || dateFrom || dateTo || tripType;

  return (
    <div className="space-y-6">
      <Card title="FE">
        <p className="text-sm text-slate-500">
          Filtrá y revisá antes de descargar el Excel: una fila por vehículo con fecha, camión, chofer,
          marca, modelo, año, VIN y si es válido, origen, destino, monto con su moneda, estado y un enlace
          al viaje en la app. Incluye una hoja Resumen con los totales por moneda.
        </p>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <Select
            value={truckId}
            onChange={(e) => setTruckId(e.target.value)}
            aria-label="Filtrar por camión"
            className="sm:w-48"
          >
            <option value="">Todos los camiones</option>
            {trucks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.plate}
              </option>
            ))}
          </Select>
          <Select
            value={zoneId}
            onChange={(e) => setZoneId(e.target.value)}
            aria-label="Filtrar por zona"
            className="sm:w-48"
          >
            <option value="">Todas las zonas</option>
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name}
              </option>
            ))}
          </Select>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 sm:w-auto"
            aria-label="Desde"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 sm:w-auto"
            aria-label="Hasta"
          />
          <Select
            value={tripType}
            onChange={(e) => setTripType(e.target.value)}
            aria-label="Filtrar por tipo de viaje"
            className="sm:w-40"
          >
            <option value="">Directo o indirecto</option>
            <option value="directo">Directo</option>
            <option value="indirecto">Indirecto</option>
          </Select>
          {hasFilters && (
            <Button variant="ghost" onClick={clearFilters}>
              Limpiar filtros
            </Button>
          )}
        </div>

        <div className="mt-4 flex items-center gap-3">
          <Button onClick={() => handleDownload("fe")} disabled={Boolean(downloading) || !rows?.length}>
            {downloading === "fe" ? "Generando..." : "Descargar Excel"}
          </Button>
          <Button variant="ghost" onClick={() => handleDownload("directos")} disabled={Boolean(downloading)}>
            {downloading === "directos" ? "Generando..." : "Formato Directos"}
          </Button>
          {!isLoading && (
            <span className="text-xs text-slate-400">
              {rows?.length ?? 0} fila{rows?.length === 1 ? "" : "s"}
            </span>
          )}
        </div>
        <div className="mt-2">
          <ErrorText>{error}</ErrorText>
        </div>
      </Card>

      <Card title="Vista previa">
        {isLoading ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : rows?.length ? (
          <div className="relative overflow-x-auto">
            <table className="w-full min-w-[960px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400">
                  <th className="py-2 pr-3 font-medium">Fecha</th>
                  <th className="py-2 pr-3 font-medium">Camión</th>
                  <th className="py-2 pr-3 font-medium">Chofer</th>
                  <th className="py-2 pr-3 font-medium">Vehículo</th>
                  <th className="py-2 pr-3 font-medium">VIN</th>
                  <th className="py-2 pr-3 font-medium">Ruta</th>
                  <th className="py-2 pr-3 font-medium">Tipo</th>
                  <th className="py-2 pr-3 font-medium">Monto</th>
                  <th className="py-2 pr-3 font-medium">Estado</th>
                  <th className="py-2 pr-3 font-medium"><span className="sr-only">Enlace</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row, i) => (
                  <tr key={`${row.trip_id}-${i}`}>
                    <td className="whitespace-nowrap py-2 pr-3 text-slate-500">
                      {new Date(`${row.trip_date}T12:00:00`).toLocaleDateString()}
                    </td>
                    <td className="py-2 pr-3 text-slate-900">
                      {[row.truck_code, row.truck_plate].filter(Boolean).join(" · ") || "—"}
                    </td>
                    <td className="py-2 pr-3 text-slate-500">{row.driver_name || "—"}</td>
                    <td className="py-2 pr-3 text-slate-900">
                      {[row.brand, row.model, row.model_year].filter(Boolean).join(" ") || "—"}
                    </td>
                    <td className="py-2 pr-3">
                      {row.vin ? (
                        <>
                          <span className="font-mono text-xs text-slate-700">{row.vin}</span>
                          {row.vin_status !== "Sí" && (
                            <span className="block text-xs text-slate-400">
                              {row.vin_status === "No" ? "No es VIN de 17" : "Dígito no cuadra"}
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-slate-500">
                      {row.origin || "?"} → {row.destination || "?"}
                    </td>
                    <td className="py-2 pr-3 text-slate-500">{TRIP_TYPE_LABEL[row.trip_type] || "—"}</td>
                    <td className="whitespace-nowrap py-2 pr-3 text-slate-900">
                      {row.amount != null ? formatMoney(row.amount, row.currency) : "—"}
                    </td>
                    <td className="py-2 pr-3">
                      {row.review === "Por revisar" ? (
                        <Badge tone="review">Revisar</Badge>
                      ) : (
                        <span className="text-xs text-slate-500">{row.status}</span>
                      )}
                    </td>
                    <td className="py-2 pr-3">
                      <Link
                        to={`/viajes/${row.trip_id}`}
                        className="text-slate-600 hover:text-slate-900 hover:underline"
                      >
                        Abrir
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>No hay viajes que coincidan con los filtros.</EmptyState>
        )}
      </Card>
    </div>
  );
}
