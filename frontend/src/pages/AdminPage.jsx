import { lazy, Suspense, useState } from "react";

import { Layout } from "../components/Layout";
import { useAuth } from "../context/AuthContext";

const DashboardSection = lazy(() => import("./admin/DashboardSection"));
const TrucksSection = lazy(() => import("./admin/TrucksSection"));
const DriversSection = lazy(() => import("./admin/DriversSection"));
const ZonesSection = lazy(() => import("./admin/ZonesSection"));
const TripsSection = lazy(() => import("./admin/TripsSection"));
const UsersSection = lazy(() => import("./admin/UsersSection"));
const FeSection = lazy(() => import("./admin/FeSection"));

const ALL_TABS = [
  { key: "dashboard", label: "Dashboard", Component: DashboardSection },
  { key: "trucks", label: "Camiones", Component: TrucksSection },
  { key: "drivers", label: "Choferes", Component: DriversSection },
  { key: "zones", label: "Zonas", Component: ZonesSection },
  { key: "trips", label: "Viajes", Component: TripsSection },
  { key: "users", label: "Usuarios", Component: UsersSection },
  { key: "fe", label: "FE", Component: FeSection, adminOnly: true },
];

export default function AdminPage() {
  const { profile } = useAuth();
  const isAdmin = profile?.role === "admin";
  const tabs = ALL_TABS.filter((tab) => !tab.adminOnly || isAdmin);
  const [active, setActive] = useState("dashboard");
  const ActiveComponent = (tabs.find((t) => t.key === active) ?? tabs[0]).Component;

  return (
    <Layout>
      <nav className="mb-6 flex gap-1 overflow-x-auto border-b border-slate-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActive(tab.key)}
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
      <Suspense fallback={<p className="text-sm text-slate-400">Cargando...</p>}>
        <ActiveComponent />
      </Suspense>
    </Layout>
  );
}
