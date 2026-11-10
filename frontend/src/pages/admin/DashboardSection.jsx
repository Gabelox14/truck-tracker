import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { formatMoney } from "../../lib/formatMoney";
import { Card, EmptyState } from "../../components/ui";
import { ForecastCard, LossesCard } from "./DashboardInsights";

function toISODate(d) {
  return d.toISOString().slice(0, 10);
}

function presetRange(preset) {
  const today = new Date();
  const to = toISODate(today);
  if (preset === "day") {
    return { dateFrom: to, dateTo: to };
  }
  if (preset === "week") {
    const from = new Date(today);
    from.setDate(from.getDate() - 6);
    return { dateFrom: toISODate(from), dateTo: to };
  }
  if (preset === "month") {
    const from = new Date(today.getFullYear(), today.getMonth(), 1);
    return { dateFrom: toISODate(from), dateTo: to };
  }
  return { dateFrom: "", dateTo: "" };
}

function Stat({ label, value, hint, className = "" }) {
  return (
    <div className={`min-w-0 sm:px-5 sm:first:pl-0 ${className}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

const DATE_INPUT =
  "w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 md:w-auto md:py-2";

// Control segmentado (mismo patrón que el selector de modo del login): carril gris, opción activa en blanco.
function Segmented({ label, options, value, onChange, className = "" }) {
  return (
    <div role="group" aria-label={label} className={`flex w-full rounded-lg bg-slate-100 p-1 ${className}`}>
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          aria-pressed={value === option.key}
          onClick={() => onChange(option.key)}
          className={`min-h-10 flex-1 whitespace-nowrap rounded-md px-3 text-sm font-medium transition md:min-h-8 md:flex-none ${
            value === option.key ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 active:text-slate-900 md:hover:text-slate-700"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function SubLabel({ children }) {
  return <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{children}</p>;
}

function DailyBarChart({ data, currency }) {
  if (!data.length) return <EmptyState>No hay datos para este rango.</EmptyState>;

  const max = Math.max(...data.map((d) => d.total), 1);
  const maxIndex = data.reduce((best, d, i) => (d.total > data[best].total ? i : best), 0);
  // Con muchos días, solo algunas etiquetas para que no se amontonen en el celular.
  const step = Math.ceil(data.length / 8);

  return (
    <div>
      <div className="sr-only">
        <table>
          <caption>Ingresos por día</caption>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Monto</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.date}>
                <td>{d.date}</td>
                <td>{formatMoney(d.total, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mb-2 text-xs text-slate-500" aria-hidden="true">
        Mejor día: {data[maxIndex].date.slice(8)}/{data[maxIndex].date.slice(5, 7)} ·{" "}
        <span className="font-medium tabular-nums text-slate-900">{formatMoney(data[maxIndex].total, currency)}</span>
      </p>
      <div className="flex h-32 items-end gap-[3px] border-b border-slate-200 md:h-40 md:gap-1.5" aria-hidden="true">
        {data.map((d, i) => (
          <div
            key={d.date}
            title={`${d.date}: ${formatMoney(d.total, currency)}`}
            className="flex h-full max-w-6 flex-1 items-end md:max-w-none"
          >
            <div
              className={`w-full rounded-t-[3px] ${i === maxIndex ? "bg-slate-900" : "bg-slate-700"}`}
              style={{ height: d.total > 0 ? `${(d.total / max) * 100}%` : "1px" }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex gap-[3px] overflow-hidden md:gap-1.5" aria-hidden="true">
        {data.map((d, i) => (
          <span key={d.date} className="max-w-6 flex-1 overflow-visible whitespace-nowrap text-[10px] text-slate-500 md:max-w-none">
            {i % step === 0 ? `${Number(d.date.slice(8))}/${Number(d.date.slice(5, 7))}` : ""}
          </span>
        ))}
      </div>
    </div>
  );
}

function TruckBarList({ data, currency }) {
  if (!data.length) return <EmptyState>No hay datos para este rango.</EmptyState>;

  const max = Math.max(...data.map((t) => t.total), 1);
  return (
    <ul className="space-y-3">
      {data.slice(0, 8).map((t) => (
        <li key={t.truck_id}>
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className="truncate text-slate-900">
              {t.code ? `${t.code} · ${t.plate}` : t.plate}
            </span>
            <span className="shrink-0 text-slate-500">{formatMoney(t.total, currency)}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full bg-slate-900"
              style={{ width: `${Math.max((t.total / max) * 100, 2)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function DashboardSection() {
  const [preset, setPreset] = useState("month");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [currency, setCurrency] = useState("CRC");

  const { dateFrom, dateTo } = useMemo(() => {
    if (preset === "custom") return { dateFrom: customFrom, dateTo: customTo };
    return presetRange(preset);
  }, [preset, customFrom, customTo]);

  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats", dateFrom, dateTo, currency],
    queryFn: async () =>
      (
        await apiClient.get("/trips/stats/summary", {
          params: {
            ...(dateFrom ? { date_from: dateFrom } : {}),
            ...(dateTo ? { date_to: dateTo } : {}),
            currency,
          },
        })
      ).data,
  });

  const presets = [
    { key: "day", label: "Día" },
    { key: "week", label: "Semana" },
    { key: "month", label: "Mes" },
    { key: "custom", label: "Rango" },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center">
          <Segmented label="Periodo" options={presets} value={preset} onChange={setPreset} className="md:w-auto" />
          {preset === "custom" && (
            <div className="grid grid-cols-2 gap-2 md:flex">
              <input
                type="date"
                value={customFrom}
                onChange={(e) => setCustomFrom(e.target.value)}
                className={DATE_INPUT}
                aria-label="Desde"
              />
              <input
                type="date"
                value={customTo}
                onChange={(e) => setCustomTo(e.target.value)}
                className={DATE_INPUT}
                aria-label="Hasta"
              />
            </div>
          )}
          {(stats?.totals_by_currency?.USD || currency === "USD") && (
            <Segmented
              label="Moneda"
              options={[
                { key: "CRC", label: "₡ Colones" },
                { key: "USD", label: "$ Dólares" },
              ]}
              value={currency}
              onChange={setCurrency}
              className="md:ml-auto md:w-auto"
            />
          )}
        </div>

        {isLoading ? (
          <p className="mt-4 text-sm text-slate-400">Cargando...</p>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-4 border-t border-slate-100 pt-4 sm:mt-5 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-slate-100 sm:pt-5">
            <Stat
              className="col-span-2 sm:col-span-1"
              label="Total generado"
              value={formatMoney(stats?.total_amount, currency)}
              hint={
                stats?.totals_by_currency?.[currency === "CRC" ? "USD" : "CRC"]
                  ? `y ${formatMoney(stats.totals_by_currency[currency === "CRC" ? "USD" : "CRC"], currency === "CRC" ? "USD" : "CRC")} en la otra moneda`
                  : undefined
              }
            />
            <Stat
              label="Cantidad de viajes"
              value={stats?.trip_count ?? 0}
              hint={stats?.pending_review ? `${stats.pending_review} por revisar` : undefined}
            />
            <Stat
              label="Camión que más generó"
              value={stats?.top_truck ? (stats.top_truck.code ?? stats.top_truck.plate) : "—"}
              hint={stats?.top_truck ? formatMoney(stats.top_truck.total, currency) : undefined}
            />
          </div>
        )}
      </Card>

      {!isLoading && (
        <Card title="Ingresos">
          <SubLabel>Por día</SubLabel>
          <div className="mt-2">
            <DailyBarChart data={stats?.by_day ?? []} currency={currency} />
          </div>

          <div className="mt-6 border-t border-slate-100 pt-6">
            <SubLabel>Por camión</SubLabel>
            <div className="mt-3">
              <TruckBarList data={stats?.by_truck ?? []} currency={currency} />
            </div>
          </div>
        </Card>
      )}

      <ForecastCard />
      <LossesCard />
    </div>
  );
}
