import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { Button, Card, EmptyState, ErrorText, Input, Select } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { apiClient } from "../../lib/apiClient";
import { formatMoney } from "../../lib/formatMoney";

const CLASS_LABEL = { liviano: "Livianos", carga: "Carga (JAC 1035/1042)" };

function useList(queryKey, path) {
  const { data } = useQuery({ queryKey, queryFn: async () => (await apiClient.get(path)).data });
  return data ?? [];
}

function RateCell({ rate, route, vehicleClass }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState("");

  const save = useMutation({
    mutationFn: async (value) =>
      rate
        ? (await apiClient.patch(`/rates/${rate.id}`, { amount: value })).data
        : (
            await apiClient.post("/rates", {
              origin_zone_id: route.origin,
              destination_zone_id: route.destination,
              vehicle_class: vehicleClass,
              amount: value,
            })
          ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rates"] });
      setEditing(false);
      showToast("Tarifa guardada");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo guardar la tarifa", "error"),
  });

  if (editing) {
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(Number(amount));
        }}
        className="flex items-center gap-1"
      >
        <Input
          type="number"
          min="1"
          step="500"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="!w-28"
          aria-label={`Tarifa ${CLASS_LABEL[vehicleClass]}`}
          autoFocus
          required
        />
        <Button type="submit" disabled={save.isPending}>
          Guardar
        </Button>
        <Button variant="ghost" type="button" onClick={() => setEditing(false)}>
          Cancelar
        </Button>
      </form>
    );
  }

  return (
    <button
      type="button"
      onClick={() => {
        setAmount(rate ? rate.amount : "");
        setEditing(true);
      }}
      className={`rounded-lg px-2 py-1 text-sm transition hover:bg-slate-100 ${rate ? "text-slate-900" : "text-slate-400"}`}
    >
      {rate ? formatMoney(rate.amount, rate.currency) : "+ Agregar"}
    </button>
  );
}

function ImportCard() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const inputId = useId();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  const upload = useMutation({
    mutationFn: async (file) => {
      const form = new FormData();
      form.append("file", file);
      return (await apiClient.post("/rates/import", form)).data;
    },
    onSuccess: (data) => {
      setSummary(data);
      setError("");
      queryClient.invalidateQueries({ queryKey: ["rates"] });
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      showToast("Tarifas importadas");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo importar el Excel"),
  });

  return (
    <Card title="Importar desde lo facturado">
      <p className="text-sm text-slate-500">
        Sube el registro de viajes directos en Excel (columnas RUTA, VEHICULO y MONTO). Por cada ruta se toma el
        monto que más se cobró; las zonas que no existan se crean.
      </p>
      <div className="mt-3">
        <label
          htmlFor={inputId}
          className={`inline-flex cursor-pointer items-center rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-slate-800 ${upload.isPending ? "pointer-events-none opacity-50" : ""}`}
        >
          {upload.isPending ? "Importando…" : "Elegir Excel"}
        </label>
        <input
          id={inputId}
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) upload.mutate(file);
          }}
        />
      </div>
      <div className="mt-3">
        <ErrorText>{error}</ErrorText>
      </div>
      {summary && (
        <div className="mt-3 space-y-1 text-sm text-slate-600" role="status" aria-live="polite">
          <p>
            {summary.rows_read} filas leídas · {summary.rates_created} tarifas nuevas · {summary.rates_updated}{" "}
            actualizadas
          </p>
          {summary.zones_created.length > 0 && <p>Zonas nuevas: {summary.zones_created.join(", ")}</p>}
          {summary.conflicts.map((conflict) => (
            <p key={`${conflict.route}-${conflict.vehicle_class}`} className="text-xs text-slate-500">
              {conflict.route} ({CLASS_LABEL[conflict.vehicle_class]}): se tomó {formatMoney(conflict.chosen)} (
              {conflict.times} veces); también se cobró{" "}
              {Object.entries(conflict.others)
                .map(([amount, times]) => `${formatMoney(Number(amount))} (${times})`)
                .join(", ")}
            </p>
          ))}
          {summary.skipped.length > 0 && (
            <p className="text-xs text-slate-500">
              Omitidas: {summary.skipped.map((item) => `${item.route} (${item.count}) — ${item.reason}`).join("; ")}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

function AddRouteForm({ zones, onAdded }) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [error, setError] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (origin === destination) {
          setError("El destino tiene que ser distinto al origen.");
          return;
        }
        setError("");
        onAdded({ origin, destination });
        setOrigin("");
        setDestination("");
      }}
      className="mt-4 space-y-2 border-t border-slate-100 pt-4"
    >
      <p className="text-xs text-slate-400">Agregar una ruta a la tabla:</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Select value={origin} onChange={(e) => setOrigin(e.target.value)} aria-label="Origen" required>
          <option value="" disabled>
            Origen
          </option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </Select>
        <Select value={destination} onChange={(e) => setDestination(e.target.value)} aria-label="Destino" required>
          <option value="" disabled>
            Destino
          </option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </Select>
        <Button type="submit">Agregar ruta</Button>
      </div>
      <ErrorText>{error}</ErrorText>
    </form>
  );
}

export default function RatesSection() {
  const rates = useList(["rates"], "/rates?category=directo");
  const zones = useList(["zones"], "/zones?limit=200");
  const [extraRoutes, setExtraRoutes] = useState([]);
  const zoneName = (id) => zones.find((z) => z.id === id)?.name ?? "?";

  const routes = new Map();
  for (const route of extraRoutes) routes.set(`${route.origin}|${route.destination}`, { ...route, rates: {} });
  for (const rate of rates) {
    const key = `${rate.origin_zone_id}|${rate.destination_zone_id}`;
    if (!routes.has(key)) routes.set(key, { origin: rate.origin_zone_id, destination: rate.destination_zone_id, rates: {} });
    routes.get(key).rates[rate.vehicle_class] = rate;
  }
  const rows = [...routes.values()].sort((a, b) =>
    `${zoneName(a.origin)} ${zoneName(a.destination)}`.localeCompare(`${zoneName(b.origin)} ${zoneName(b.destination)}`),
  );

  return (
    <div className="space-y-6">
      <Card title="Tarifas de viajes directos">
        <p className="text-sm text-slate-500">
          En los viajes directos el monto lo fija la ruta: cada vehículo toma la tarifa de su ruta y clase, y el total
          del viaje es la suma. La misma tarifa vale en los dos sentidos si solo hay una cargada.
        </p>
        {rows.length ? (
          <div className="relative mt-4 overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400">
                  <th className="py-2 pr-3 font-medium">Ruta</th>
                  <th className="py-2 pr-3 font-medium">{CLASS_LABEL.liviano}</th>
                  <th className="py-2 pr-3 font-medium">{CLASS_LABEL.carga}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((route) => (
                  <tr key={`${route.origin}|${route.destination}`}>
                    <td className="py-2 pr-3 text-slate-900">
                      {zoneName(route.origin)} → {zoneName(route.destination)}
                    </td>
                    {["liviano", "carga"].map((vehicleClass) => (
                      <td key={vehicleClass} className="py-1 pr-3">
                        <RateCell rate={route.rates[vehicleClass]} route={route} vehicleClass={vehicleClass} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>Todavía no hay tarifas. Impórtalas desde el registro facturado o agrega una ruta.</EmptyState>
        )}
        <AddRouteForm zones={zones} onAdded={(route) => setExtraRoutes((list) => [...list, route])} />
      </Card>
      <ImportCard />
    </div>
  );
}
