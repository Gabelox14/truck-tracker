import { useState } from "react";

import { Layout } from "../components/Layout";
import DriversSection from "./admin/DriversSection";
import TripsSection from "./admin/TripsSection";
import TrucksSection from "./admin/TrucksSection";
import UsersSection from "./admin/UsersSection";
import ZonesSection from "./admin/ZonesSection";

const TABS = [
  { key: "trucks", label: "Camiones", Component: TrucksSection },
  { key: "drivers", label: "Choferes", Component: DriversSection },
  { key: "zones", label: "Zonas", Component: ZonesSection },
  { key: "trips", label: "Viajes", Component: TripsSection },
  { key: "users", label: "Usuarios", Component: UsersSection },
];

export default function AdminPage() {
  const [active, setActive] = useState("trucks");
  const ActiveComponent = TABS.find((t) => t.key === active).Component;

  return (
    <Layout>
      <nav className="mb-6 flex gap-1 border-b border-slate-200">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActive(tab.key)}
            className={`border-b-2 px-3 py-2 text-sm font-medium transition ${
              active === tab.key
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <ActiveComponent />
    </Layout>
  );
}
