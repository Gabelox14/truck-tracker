import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../../lib/apiClient";
import { Card, EmptyState } from "../../components/ui";

const MONTHS_SHORT = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MONTHS_LONG = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

// Colones redondeados: en el análisis los céntimos solo estorban.
function crc(value) {
  return `₡${Math.round(Number(value ?? 0)).toLocaleString("en-US")}`;
}

function number(value, digits = 0) {
  return Number(value ?? 0).toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function monthIndex(month) {
  return Number(month.slice(5, 7)) - 1;
}

function monthLong(month) {
  return `${MONTHS_LONG[monthIndex(month)]} ${month.slice(0, 4)}`;
}

// ["2026-06", "2026-08", "2026-10"] -> "jun, ago y oct 2026"
function monthList(months) {
  if (!months?.length) return "";
  const names = months.map((m) => MONTHS_SHORT[monthIndex(m)]);
  const years = [...new Set(months.map((m) => m.slice(0, 4)))].join("–");
  const list = names.length === 1 ? names[0] : `${names.slice(0, -1).join(", ")} y ${names.at(-1)}`;
  return `${list} ${years}`;
}

function shortDate(iso) {
  const [year, month, day] = iso.split("-");
  return `${Number(day)} ${MONTHS_SHORT[Number(month) - 1]} ${year}`;
}

function daysSince(iso) {
  return Math.floor((Date.now() - new Date(`${iso}T12:00:00`).getTime()) / 86400000);
}

function useStats(path) {
  return useQuery({
    queryKey: ["dashboard", path],
    queryFn: async () => (await apiClient.get(`/trips/stats/${path}`)).data,
    staleTime: 5 * 60 * 1000,
  });
}

function Loading() {
  return (
    <div className="space-y-3" aria-hidden="true">
      <div className="h-4 w-1/3 animate-pulse rounded bg-slate-100" />
      <div className="h-8 w-1/2 animate-pulse rounded bg-slate-100" />
      <div className="h-32 animate-pulse rounded bg-slate-100" />
    </div>
  );
}

function Failed() {
  return <EmptyState>No se pudo calcular. Recargá la página para intentar de nuevo.</EmptyState>;
}

/* --- Proyección -------------------------------------------------------------- */

const BAR_STYLE = {
  basis: "bg-slate-900",
  normal: "bg-slate-400",
  partial: "bg-slate-200",
  forecast:
    "border-[1.5px] border-slate-900 bg-[repeating-linear-gradient(45deg,#0f172a_0,#0f172a_1px,transparent_1px,transparent_5px)]",
};
const KIND_LABEL = {
  basis: "Base de la proyección",
  normal: "Mes completo",
  partial: "Registro incompleto",
  forecast: "Proyección",
};

// Barras en HTML (no SVG) para que las etiquetas mantengan su tamaño en el celular.
function MonthChart({ history, target, forecast }) {
  const bars = [
    ...history.map((h) => ({ ...h, kind: h.basis ? "basis" : h.normal ? "normal" : "partial" })),
    { month: target, amount: forecast.amount, low: forecast.low, high: forecast.high, kind: "forecast" },
  ];
  const max = Math.max(...bars.map((b) => b.high ?? b.amount), 1);
  const pct = (value) => `${(value / max) * 100}%`;

  return (
    <figure>
      <table className="sr-only">
        <caption>Ingresos por mes y proyección</caption>
        <thead>
          <tr>
            <th>Mes</th>
            <th>Ingresos</th>
            <th>Tipo</th>
          </tr>
        </thead>
        <tbody>
          {bars.map((b) => (
            <tr key={b.month}>
              <td>{monthLong(b.month)}</td>
              <td>{b.kind === "forecast" ? `${crc(b.amount)} (entre ${crc(b.low)} y ${crc(b.high)})` : crc(b.amount)}</td>
              <td>{KIND_LABEL[b.kind]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex h-36 items-end gap-1 border-b border-slate-200 sm:gap-1.5" aria-hidden="true">
        {bars.map((b) => (
          <div
            key={b.month}
            className="group relative flex h-full flex-1 items-end"
            title={
              b.kind === "forecast"
                ? `${monthLong(b.month)}: proyección ${crc(b.amount)} (entre ${crc(b.low)} y ${crc(b.high)})`
                : `${monthLong(b.month)}: ${crc(b.amount)}${b.kind === "partial" ? " · registro incompleto" : ""}`
            }
          >
            <div
              className={`w-full rounded-t-[4px] transition-opacity group-hover:opacity-80 ${BAR_STYLE[b.kind]}`}
              style={{ height: b.amount > 0 ? pct(b.amount) : "1px" }}
            />
            {b.kind === "forecast" && (
              <div
                className="absolute left-1/2 w-2.5 -translate-x-1/2 border-y-2 border-slate-900"
                style={{ bottom: pct(b.low), height: `calc(${pct(b.high)} - ${pct(b.low)})` }}
              >
                <div className="mx-auto h-full w-0.5 bg-slate-900" />
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex gap-1 sm:gap-1.5" aria-hidden="true">
        {bars.map((b, i) => {
          const label = MONTHS_SHORT[monthIndex(b.month)];
          return (
            <span
              key={b.month}
              className={`flex-1 text-center text-[10px] leading-tight tracking-tight sm:text-[11px] ${
                b.kind === "forecast" ? "font-semibold text-slate-900" : "text-slate-500"
              }`}
            >
              {label}
              {(i === 0 || label === "ene") && (
                <span className="block text-[10px] text-slate-400">{b.month.slice(0, 4)}</span>
              )}
            </span>
          );
        })}
      </div>
      <figcaption className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        {["basis", "normal", "partial", "forecast"].map((kind) => (
          <span key={kind} className="inline-flex items-center gap-1.5">
            <span className={`h-2.5 w-2.5 rounded-sm ${BAR_STYLE[kind]}`} aria-hidden="true" />
            {kind === "forecast" ? "Proyección y rango" : KIND_LABEL[kind]}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

export function ForecastCard() {
  const { data, isLoading, isError } = useStats("forecast");
  const target = data?.target_month;

  return (
    <Card title="Proyección" action={target && <span className="text-xs text-slate-500">{monthLong(target)}</span>}>
      {isLoading ? (
        <Loading />
      ) : isError ? (
        <Failed />
      ) : !data.fleet ? (
        <EmptyState>Hace falta al menos un mes completo de viajes para proyectar.</EmptyState>
      ) : (
        <div className="space-y-6">
          {data.last_trip_date && daysSince(data.last_trip_date) > 7 && (
            <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
              El último viaje registrado es del {shortDate(data.last_trip_date)}. Lo que va de{" "}
              {MONTHS_LONG[monthIndex(data.current_month.month)]} todavía no está cargado, así que la proyección sale de
              los meses anteriores.
            </p>
          )}

          <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-end">
            <div>
              <p className="text-sm text-slate-500">
                {monthLong(target)[0].toUpperCase() + monthLong(target).slice(1)} debería cerrar en
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{crc(data.fleet.amount)}</p>
              <p className="mt-1 text-sm text-slate-600">
                entre <span className="tabular-nums">{crc(data.fleet.low)}</span> y{" "}
                <span className="tabular-nums">{crc(data.fleet.high)}</span>, con unos {number(data.fleet.trips)} viajes y{" "}
                {number(data.fleet.cars)} carros.
              </p>
              <p className="mt-4 text-xs leading-relaxed text-slate-500">
                Promedio de {monthList(data.basis_months)}, los últimos meses con registro completo. Cada camión cuenta
                desde el mes en que empezó a trabajar.
                {data.same_month_last_year && (
                  <>
                    {" "}
                    {MONTHS_LONG[monthIndex(data.same_month_last_year.month)][0].toUpperCase() +
                      MONTHS_LONG[monthIndex(data.same_month_last_year.month)].slice(1)}{" "}
                    {data.same_month_last_year.month.slice(0, 4)} cerró en{" "}
                    <span className="tabular-nums">{crc(data.same_month_last_year.amount)}</span>
                    {!data.same_month_last_year.normal && " (con registro incompleto)"}.
                  </>
                )}
              </p>
            </div>
            <MonthChart history={data.history} target={target} forecast={data.fleet} />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-500">
                  <th className="py-2 pr-3 font-medium">Camión</th>
                  <th className="py-2 pr-3 text-right font-medium">Proyección</th>
                  <th className="py-2 pr-3 text-right font-medium">Rango</th>
                  <th className="py-2 pr-3 text-right font-medium">Viajes</th>
                  <th className="py-2 text-right font-medium">Carros</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 tabular-nums">
                {data.by_unit.map((u) => (
                  <tr key={u.unit}>
                    <td className="py-2 pr-3 text-slate-900">
                      {u.unit}
                      {u.months < data.basis_months.length && (
                        <span className="ml-2 text-xs text-slate-400">
                          {u.months} {u.months === 1 ? "mes" : "meses"} de historia
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-right font-medium text-slate-900">{crc(u.amount)}</td>
                    <td className="py-2 pr-3 text-right text-slate-500">
                      {crc(u.low)} – {crc(u.high)}
                    </td>
                    <td className="py-2 pr-3 text-right text-slate-600">{number(u.trips)}</td>
                    <td className="py-2 text-right text-slate-600">{number(u.cars)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
  );
}

/* --- Dónde se pierde plata ---------------------------------------------------- */

function route(r) {
  return `${r.origin} → ${r.destination}`;
}

function joinNames(names) {
  return names.length === 1 ? names[0] : `${names.slice(0, -1).join(", ")} y ${names.at(-1)}`;
}

function buildFindings(data) {
  const findings = [];
  const routesByKey = Object.fromEntries(data.routes.map((r) => [route(r), r]));

  if (data.pending_review.trips > 0) {
    findings.push({
      key: "review",
      title: `${number(data.pending_review.trips)} viajes con VIN por corregir`,
      evidence:
        "El VIN no cuadra (dígito verificador, largo o marca). Facturar así arriesga que el cliente devuelva la factura.",
      action: "Corregirlos en la pestaña Por revisar, empezando por los de mayor monto.",
      value: crc(data.pending_review.amount),
      unit: "en total",
    });
  }

  data.capacity.slice(0, 3).forEach((c) => {
    findings.push({
      key: `capacity-${c.unit}`,
      title: `${c.unit} salió ${number(c.under_trips)} veces ${
        c.typical_load === 2 ? "con un solo carro" : `con menos de ${c.typical_load} carros`
      }`,
      evidence: `La mitad de sus viajes lleva ${c.typical_load} o más, pero el ${number(c.under_share * 100)} % salió con menos. Donde más pasa: ${route(c.top_route)} (${c.top_route.trips} viajes).`,
      action: `Juntar carros con el mismo destino antes de despachar a ${c.unit}, sobre todo en ${route(c.top_route)}.`,
      value: crc(c.opportunity_per_month),
      unit: "al mes, con su carga habitual",
    });
  });

  data.empty_legs.slice(0, 2).forEach((leg) => {
    const paid = routesByKey[route(leg)];
    findings.push({
      key: `empty-${route(leg)}`,
      title: `${route(leg)}: ${number(leg.trips_per_month)} regresos vacíos al mes`,
      evidence: paid
        ? `Unos ${number(leg.km_per_month)} km al mes sin carga, en una ruta que también tiene ${number(paid.trips_per_month)} viajes pagados al mes.`
        : `Unos ${number(leg.km_per_month)} km al mes sin carga para volver a ${leg.destination}.`,
      action: paid
        ? `Coordinar esos viajes pagados con los regresos: el camión ya hace el recorrido.`
        : `Buscar carros para traer de ${leg.origin} cuando un camión termina allá.`,
      value: `${number(leg.km_per_month)} km`,
      unit: "vacíos al mes",
    });
  });

  if (data.rebotes.trips > 0) {
    findings.push({
      key: "rebotes",
      title: `${number(data.rebotes.trips)} rebotes cobrados a mitad de precio`,
      evidence: `Se cobraron ${crc(data.rebotes.amount)}; a precio completo habrían sido el doble.`,
      action: "Revisar por qué vuelven esos carros y si el cliente debe pagar el viaje completo.",
      value: crc(data.rebotes.per_month),
      unit: "al mes sin cobrar",
    });
  }

  const fleetPerKm = data.fleet_amount_per_km;
  data.routes
    .filter((r) => r.low_pay)
    .sort((a, b) => (fleetPerKm - b.amount_per_km) * b.trips - (fleetPerKm - a.amount_per_km) * a.trips)
    .slice(0, 3)
    .forEach((r) => {
      findings.push({
        key: `route-${route(r)}`,
        title: `${route(r)} paga ${crc(r.amount_per_km)} por km`,
        evidence: `La flota promedia ${crc(fleetPerKm)} por km. Son ${number(r.km)} km de ida (la vuelta suele ser vacía), ${number(r.trips_per_month, 1)} viajes al mes y ${crc(r.amount_per_trip)} por viaje con ${number(r.cars_per_trip, 1)} carros.`,
        action:
          r.cars_per_trip < 2
            ? "Llevar más carros por viaje en esta ruta o revisar la tarifa."
            : "Revisar la tarifa o conseguir carga para la vuelta.",
        value: `${crc(r.amount_per_km)}/km`,
        unit: `vs ${crc(fleetPerKm)} de la flota`,
      });
    });

  const idle = data.units
    .filter((u) => u.days_per_month <= 12)
    .sort((a, b) => a.days_per_month - b.days_per_month)
    .slice(0, 3);
  if (idle.length) {
    const days = idle.map((u) => u.days_per_month);
    const best = idle.reduce((a, b) => (b.amount_per_day > a.amount_per_day ? b : a));
    findings.push({
      key: "idle",
      title: `${joinNames(idle.map((u) => u.unit))} trabajan ${number(Math.min(...days))} a ${number(Math.max(...days))} de 22 días hábiles`,
      evidence: `Cada día que ${best.unit} trabaja deja unos ${crc(best.amount_per_day)}.`,
      action: "Pasarles viajes cuando los camiones más cargados estén llenos, en vez de esperar al día siguiente.",
      value: `${number(22 - Math.min(...days))} días`,
      unit: "parados al mes, el que más",
    });
  }
  return findings;
}

function Finding({ finding }) {
  return (
    <li className="grid gap-3 py-4 first:pt-0 last:pb-0 sm:grid-cols-[minmax(0,1fr)_11rem] sm:gap-6">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">{finding.title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-slate-600">{finding.evidence}</p>
        <p className="mt-2 text-sm text-slate-900">
          <span className="font-medium">Qué hacer:</span> {finding.action}
        </p>
      </div>
      <div className="sm:text-right">
        <p className="text-base font-semibold tabular-nums text-slate-900">{finding.value}</p>
        <p className="text-xs text-slate-500">{finding.unit}</p>
      </div>
    </li>
  );
}

function UnitsTable({ units, fleetPerKm }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs text-slate-500">
            <th className="py-2 pr-3 font-medium">Camión</th>
            <th className="py-2 pr-3 text-right font-medium">Días / mes</th>
            <th className="py-2 pr-3 text-right font-medium">Viajes / mes</th>
            <th className="py-2 pr-3 text-right font-medium">Carros / viaje</th>
            <th className="py-2 pr-3 text-right font-medium">Km / mes</th>
            <th className="py-2 pr-3 text-right font-medium">Km vacíos</th>
            <th className="py-2 pr-3 text-right font-medium">₡ / km</th>
            <th className="py-2 text-right font-medium">₡ / mes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 tabular-nums">
          {units.map((u) => (
            <tr key={u.unit}>
              <td className="py-2 pr-3">
                <span className="text-slate-900">{u.unit}</span>
                <span className="ml-2 text-xs text-slate-400">{u.kind}</span>
              </td>
              <td className="py-2 pr-3 text-right text-slate-600">{number(u.days_per_month, 1)}</td>
              <td className="py-2 pr-3 text-right text-slate-600">{number(u.trips_per_month, 1)}</td>
              <td className="py-2 pr-3 text-right text-slate-600">{number(u.cars_per_trip, 1)}</td>
              <td className="py-2 pr-3 text-right text-slate-600">{u.km_per_month != null ? number(u.km_per_month) : "—"}</td>
              <td className="py-2 pr-3 text-right text-slate-600">
                {u.empty_share != null ? `${number(u.empty_share * 100)} %` : "—"}
              </td>
              <td
                className={`py-2 pr-3 text-right ${
                  fleetPerKm && u.amount_per_km < fleetPerKm ? "font-medium text-slate-900" : "text-slate-600"
                }`}
              >
                {u.amount_per_km != null ? crc(u.amount_per_km) : "—"}
              </td>
              <td className="py-2 text-right font-medium text-slate-900">{crc(u.amount_per_month)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function LossesCard() {
  const { data, isLoading, isError } = useStats("insights");
  const findings = data ? buildFindings(data) : [];

  return (
    <Card
      title="Dónde se pierde plata"
      action={data?.window_months?.length > 0 && <span className="text-xs text-slate-500">{monthList(data.window_months)}</span>}
    >
      {isLoading ? (
        <Loading />
      ) : isError ? (
        <Failed />
      ) : !data.window_months.length ? (
        <EmptyState>Hace falta al menos un mes completo de viajes para analizar.</EmptyState>
      ) : (
        <div className="space-y-8">
          {findings.length ? (
            <ol className="divide-y divide-slate-100">
              {findings.map((f) => (
                <Finding key={f.key} finding={f} />
              ))}
            </ol>
          ) : (
            <EmptyState>No aparece nada fuera de lo normal en estos meses.</EmptyState>
          )}

          <section className="border-t border-slate-100 pt-6">
            <h3 className="text-sm font-semibold text-slate-900">Por camión</h3>
            <p className="mt-1 text-sm text-slate-600">
              Promedio de un mes en {monthList(data.window_months)}. En negrita, el ₡ por km por debajo de la flota (
              {crc(data.fleet_amount_per_km)}).
            </p>
            <div className="mt-3">
              <UnitsTable units={data.units} fleetPerKm={data.fleet_amount_per_km} />
            </div>
            <p className="mt-3 text-xs leading-relaxed text-slate-500">
              Los km son aproximados: salen de la distancia por carretera entre zonas y de suponer que cada día empieza y
              termina en {data.base_zone ?? "la zona base"}. No hay GPS.
              {data.km_coverage != null && data.km_coverage < 1 &&
                ` ${number((1 - data.km_coverage) * 100)} % de los días quedó fuera porque alguna ruta no tiene distancia cargada.`}
            </p>
          </section>
        </div>
      )}
    </Card>
  );
}
