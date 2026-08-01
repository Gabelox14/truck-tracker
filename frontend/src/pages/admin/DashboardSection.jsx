import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Button, Card, EmptyState } from "../../components/ui";

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

function formatMoney(value) {
  return `$${Number(value ?? 0).toFixed(2)}`;
}

function Stat({ label, value, hint }) {
  return (
    <div className="py-3 first:pt-0 sm:px-5 sm:py-0 sm:first:pl-0">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function SubLabel({ children }) {
  return <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{children}</p>;
}

function DailyBarChart({ data }) {
  if (!data.length) return <EmptyState>No hay datos para este rango.</EmptyState>;

  const width = 640;
  const height = 160;
  const barGap = 6;
  const barWidth = Math.min(24, (width - barGap * (data.length - 1)) / data.length);
  const max = Math.max(...data.map((d) => d.total), 1);
  const maxIndex = data.reduce((best, d, i) => (d.total > data[best].total ? i : best), 0);

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${Math.max(width, data.length * (barWidth + barGap))} ${height + 24}`}
        className="h-40 w-full"
        role="img"
        aria-label="Ingresos por día"
      >
        <line x1="0" y1={height} x2={data.length * (barWidth + barGap)} y2={height} stroke="#e2e8f0" strokeWidth="1" />
        {data.map((d, i) => {
          const barHeight = (d.total / max) * (height - 8);
          const x = i * (barWidth + barGap);
          const y = height - barHeight;
          return (
            <g key={d.date}>
              <title>{`${d.date}: ${formatMoney(d.total)}`}</title>
              <rect x={x} y={y} width={barWidth} height={Math.max(barHeight, 1)} rx="4" fill="#0f172a" />
              {i === maxIndex && d.total > 0 && (
                <text x={x + barWidth / 2} y={y - 4} textAnchor="middle" fontSize="10" fill="#475569">
                  {formatMoney(d.total)}
                </text>
              )}
              <text x={x + barWidth / 2} y={height + 14} textAnchor="middle" fontSize="9" fill="#94a3b8">
                {d.date.slice(5)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function TruckBarList({ data }) {
  if (!data.length) return <EmptyState>No hay datos para este rango.</EmptyState>;

  const max = Math.max(...data.map((t) => t.total), 1);
  return (
    <ul className="space-y-3">
      {data.slice(0, 8).map((t) => (
        <li key={t.truck_id}>
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className="truncate text-slate-900">
              {t.plate}
              {t.code ? ` · ${t.code}` : ""}
            </span>
            <span className="shrink-0 text-slate-500">{formatMoney(t.total)}</span>
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

  const { dateFrom, dateTo } = useMemo(() => {
    if (preset === "custom") return { dateFrom: customFrom, dateTo: customTo };
    return presetRange(preset);
  }, [preset, customFrom, customTo]);

  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats", dateFrom, dateTo],
    queryFn: async () =>
      (
        await apiClient.get("/trips/stats/summary", {
          params: {
            ...(dateFrom ? { date_from: dateFrom } : {}),
            ...(dateTo ? { date_to: dateTo } : {}),
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
        <div className="flex flex-wrap items-center gap-2">
          {presets.map((p) => (
            <Button
              key={p.key}
              variant={preset === p.key ? "primary" : "ghost"}
              onClick={() => setPreset(p.key)}
            >
              {p.label}
            </Button>
          ))}
          {preset === "custom" && (
            <>
              <input
                type="date"
                value={customFrom}
                onChange={(e) => setCustomFrom(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900"
                aria-label="Desde"
              />
              <input
                type="date"
                value={customTo}
                onChange={(e) => setCustomTo(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900"
                aria-label="Hasta"
              />
            </>
          )}
        </div>

        {isLoading ? (
          <p className="mt-4 text-sm text-slate-400">Cargando...</p>
        ) : (
          <div className="mt-5 grid grid-cols-1 divide-y divide-slate-100 border-t border-slate-100 pt-4 sm:grid-cols-3 sm:divide-x sm:divide-y-0 sm:pt-5">
            <Stat label="Total generado" value={formatMoney(stats?.total_amount)} />
            <Stat label="Cantidad de viajes" value={stats?.trip_count ?? 0} />
            <Stat
              label="Camión que más generó"
              value={stats?.top_truck ? stats.top_truck.plate : "—"}
              hint={stats?.top_truck ? formatMoney(stats.top_truck.total) : undefined}
            />
          </div>
        )}
      </Card>

      {!isLoading && (
        <Card title="Ingresos">
          <SubLabel>Por día</SubLabel>
          <div className="mt-2">
            <DailyBarChart data={stats?.by_day ?? []} />
          </div>

          <div className="mt-6 border-t border-slate-100 pt-6">
            <SubLabel>Por camión</SubLabel>
            <div className="mt-3">
              <TruckBarList data={stats?.by_truck ?? []} />
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
