import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";

import { icons } from "../components/icons";
import { Layout, ROLE_LABEL } from "../components/Layout";
import { useAuth } from "../context/AuthContext";

const DashboardSection = lazy(() => import("./admin/DashboardSection"));
const TrucksSection = lazy(() => import("./admin/TrucksSection"));
const DriversSection = lazy(() => import("./admin/DriversSection"));
const ZonesSection = lazy(() => import("./admin/ZonesSection"));
const TripsSection = lazy(() => import("./admin/TripsSection"));
const UsersSection = lazy(() => import("./admin/UsersSection"));
const FeSection = lazy(() => import("./admin/FeSection"));
const ReviewSection = lazy(() => import("./admin/ReviewSection"));
const RatesSection = lazy(() => import("./admin/RatesSection"));

const ALL_TABS = [
  { key: "dashboard", label: "Dashboard", icon: "dashboard", Component: DashboardSection },
  { key: "review", label: "Por revisar", icon: "review", Component: ReviewSection },
  { key: "trucks", label: "Camiones", icon: "trucks", Component: TrucksSection },
  { key: "drivers", label: "Choferes", icon: "drivers", Component: DriversSection },
  { key: "zones", label: "Zonas", icon: "zones", Component: ZonesSection },
  { key: "trips", label: "Viajes", icon: "trips", Component: TripsSection },
  { key: "users", label: "Usuarios", icon: "users", Component: UsersSection },
  { key: "rates", label: "Tarifas", icon: "rates", Component: RatesSection, adminOnly: true },
  { key: "fe", label: "FE", icon: "fe", Component: FeSection, adminOnly: true },
];

// En el celular, las secciones del día a día van en la barra de abajo; el resto, en "Más".
const PRIMARY_ADMIN = ["dashboard", "review", "trips", "fe"];
const PRIMARY_STAFF = ["dashboard", "review", "trips", "trucks"];

function MoreSheet({ open, onClose, tabs, active, onSelect, roleLabel, onSignOut }) {
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => event.key === "Escape" && onClose();
    const previous = document.body.style.overflow;
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    panelRef.current?.querySelector("button")?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [open, onClose]);

  return (
    <div className={`fixed inset-0 z-40 md:hidden ${open ? "" : "pointer-events-none"}`} inert={!open}>
      <div
        className={`absolute inset-0 bg-slate-900/40 transition-opacity duration-200 motion-reduce:transition-none ${
          open ? "opacity-100" : "opacity-0"
        }`}
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Más secciones"
        className={`pb-safe absolute inset-x-0 bottom-0 rounded-t-2xl bg-white shadow-[0_-8px_24px_rgb(15_23_42/0.12)] transition-transform duration-200 ease-out motion-reduce:transition-none ${
          open ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="mx-auto mt-2.5 h-1 w-10 rounded-full bg-slate-200" aria-hidden="true" />
        <ul className="px-2 pb-1 pt-2">
          {tabs.map((tab) => {
            const Icon = icons[tab.icon];
            const current = tab.key === active;
            return (
              <li key={tab.key}>
                <button
                  type="button"
                  onClick={() => onSelect(tab.key)}
                  aria-current={current ? "page" : undefined}
                  className={`flex min-h-12 w-full items-center gap-3 rounded-lg px-3 text-left text-[15px] transition active:bg-slate-100 ${
                    current ? "bg-slate-100 font-medium text-slate-900" : "text-slate-700"
                  }`}
                >
                  <Icon className="h-5 w-5 shrink-0 text-slate-500" />
                  <span className="flex-1">{tab.label}</span>
                  <icons.chevron className="h-4 w-4 text-slate-300" />
                </button>
              </li>
            );
          })}
        </ul>
        <div className="mx-4 flex items-center justify-between border-t border-slate-100 py-2">
          <span className="text-sm text-slate-500">{roleLabel}</span>
          <button
            type="button"
            onClick={onSignOut}
            className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm font-medium text-slate-700 active:bg-slate-100"
          >
            <icons.logout className="h-4 w-4" />
            Salir
          </button>
        </div>
      </div>
    </div>
  );
}

function BottomNav({ tabs, more, active, onSelect, onMore, moreOpen }) {
  const moreActive = moreOpen || more.some((tab) => tab.key === active);
  const item = (key, label, Icon, current, onClick, extra = {}) => (
    <li key={key}>
      <button
        type="button"
        onClick={onClick}
        className={`relative flex h-14 w-full flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition active:bg-slate-50 ${
          current ? "text-slate-900" : "text-slate-500"
        }`}
        {...extra}
      >
        {current && <span className="absolute inset-x-5 top-0 h-0.5 rounded-full bg-slate-900" aria-hidden="true" />}
        <Icon className="h-[22px] w-[22px]" />
        <span className="max-w-full truncate px-1">{label}</span>
      </button>
    </li>
  );

  return (
    <nav aria-label="Secciones" className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white md:hidden">
      <ul className="mx-auto grid max-w-md grid-cols-5">
        {tabs.map((tab) =>
          item(tab.key, tab.label, icons[tab.icon], tab.key === active && !moreOpen, () => onSelect(tab.key), {
            "aria-current": tab.key === active ? "page" : undefined,
          }),
        )}
        {item("more", "Más", icons.more, moreActive, onMore, { "aria-expanded": moreOpen, "aria-haspopup": "dialog" })}
      </ul>
    </nav>
  );
}

export default function AdminPage() {
  const { profile, signOut } = useAuth();
  const isAdmin = profile?.role === "admin";
  const tabs = ALL_TABS.filter((tab) => !tab.adminOnly || isAdmin);
  const primaryKeys = isAdmin ? PRIMARY_ADMIN : PRIMARY_STAFF;
  const primary = primaryKeys.map((key) => tabs.find((tab) => tab.key === key)).filter(Boolean);
  const more = tabs.filter((tab) => !primaryKeys.includes(tab.key));
  const [active, setActive] = useState("dashboard");
  const [visited, setVisited] = useState(() => new Set(["dashboard"]));
  const [moreOpen, setMoreOpen] = useState(false);
  const activeTab = tabs.find((tab) => tab.key === active) ?? tabs[0];

  function selectTab(key) {
    setMoreOpen(false);
    if (key !== active) window.scrollTo({ top: 0 });
    setActive(key);
    setVisited((prev) => (prev.has(key) ? prev : new Set(prev).add(key)));
  }

  const closeMore = useCallback(() => setMoreOpen(false), []);

  return (
    <Layout
      bottomNav={
        <>
          <BottomNav
            tabs={primary}
            more={more}
            active={active}
            moreOpen={moreOpen}
            onSelect={selectTab}
            onMore={() => setMoreOpen((open) => !open)}
          />
          <MoreSheet
            open={moreOpen}
            onClose={closeMore}
            tabs={more}
            active={active}
            onSelect={selectTab}
            roleLabel={ROLE_LABEL[profile?.role] ?? profile?.role}
            onSignOut={signOut}
          />
        </>
      }
    >
      <nav className="mb-6 hidden gap-1 overflow-x-auto border-b border-slate-200 md:flex">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => selectTab(tab.key)}
            className={`shrink-0 whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition ${
              active === tab.key
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <h2 className="mb-4 text-xl font-semibold tracking-tight text-slate-900 md:hidden">{activeTab.label}</h2>
      {tabs
        .filter((tab) => visited.has(tab.key))
        .map((tab) => (
          <div key={tab.key} className={tab.key === active ? undefined : "hidden"}>
            <Suspense fallback={<p className="text-sm text-slate-400">Cargando...</p>}>
              <tab.Component />
            </Suspense>
          </div>
        ))}
    </Layout>
  );
}
