import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Button, Card, EmptyState, ErrorText, Select } from "../../components/ui";
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

  async function handleDownload() {
    setError("");
    setDownloading(true);
    try {
      const response = await apiClient.get("/trips/export/fe", {
        params: buildParams(filters),
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "FE.xlsx";
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
          Filtrá y revisá el resumen antes de descargar el Excel: código de camión, placa,
          destino inicial y final, monto, marca del carro y un enlace a la foto del VIN.
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
          <Button onClick={handleDownload} disabled={downloading || !rows?.length}>
            {downloading ? "Generando..." : "Descargar Excel"}
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
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400">
                  <th className="py-2 pr-3 font-medium">Código</th>
                  <th className="py-2 pr-3 font-medium">Placa</th>
                  <th className="py-2 pr-3 font-medium">Destino inicial</th>
                  <th className="py-2 pr-3 font-medium">Destino final</th>
                  <th className="py-2 pr-3 font-medium">Tipo</th>
                  <th className="py-2 pr-3 font-medium">Monto</th>
                  <th className="py-2 pr-3 font-medium">Marca</th>
                  <th className="py-2 pr-3 font-medium">VIN</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row, i) => (
                  <tr key={i}>
                    <td className="py-2 pr-3 text-slate-900">{row.truck_code || "—"}</td>
                    <td className="py-2 pr-3 text-slate-900">{row.truck_plate || "—"}</td>
                    <td className="py-2 pr-3 text-slate-500">{row.origin || "—"}</td>
                    <td className="py-2 pr-3 text-slate-500">{row.destination || "—"}</td>
                    <td className="py-2 pr-3 text-slate-500">
                      {TRIP_TYPE_LABEL[row.trip_type] || "—"}
                    </td>
                    <td className="py-2 pr-3 text-slate-900">
                      {row.amount != null ? `$${Number(row.amount).toFixed(2)}` : "—"}
                    </td>
                    <td className="py-2 pr-3 text-slate-500">{row.brand || "—"}</td>
                    <td className="py-2 pr-3">
                      {row.vin_photo_url ? (
                        <a
                          href={row.vin_photo_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-600 hover:text-slate-900 hover:underline"
                        >
                          Ver foto
                        </a>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
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
