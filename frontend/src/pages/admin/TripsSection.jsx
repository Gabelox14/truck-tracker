import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Badge, Button, Card, EmptyState, Input } from "../../components/ui";
import { TripCarsPanel } from "../../components/TripCarsPanel";

function useLookup(queryKey, path, labelKey) {
  const { data } = useQuery({
    queryKey,
    queryFn: async () => (await apiClient.get(path)).data,
  });
  const map = {};
  for (const item of data ?? []) {
    map[item.id] = item[labelKey];
  }
  return map;
}

function AmountEditor({ trip }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState(trip.amount ?? "");

  const setTripAmount = useMutation({
    mutationFn: async (value) =>
      (await apiClient.patch(`/trips/${trip.id}/amount`, { amount: Number(value) })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      setEditing(false);
    },
  });

  if (editing) {
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setTripAmount.mutate(amount);
        }}
        className="flex items-center gap-1"
      >
        <Input
          type="number"
          step="0.01"
          min="0"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="!w-28"
          autoFocus
          required
        />
        <Button type="submit" disabled={setTripAmount.isPending}>
          Guardar
        </Button>
      </form>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className="text-sm text-slate-600 hover:text-slate-900 hover:underline"
    >
      {trip.amount != null ? `$${Number(trip.amount).toFixed(2)}` : "Agregar monto"}
    </button>
  );
}

function TripRow({ trip, driverNames, truckPlates, zoneNames }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <li className="py-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-900">
          {driverNames[trip.driver_id] ?? "Chofer"} · {truckPlates[trip.truck_id] ?? "Camión"}
        </span>
        <Badge tone={trip.status === "completed" ? "emerald" : "amber"}>
          {trip.status === "completed" ? "Completado" : "En curso"}
        </Badge>
      </div>
      <p className="mt-1 text-sm text-slate-500">
        {zoneNames[trip.origin_zone_id] ?? "?"} → {zoneNames[trip.destination_zone_id] ?? "?"}
      </p>
      <p className="mt-0.5 text-xs text-slate-400">
        Salió {new Date(trip.started_at).toLocaleString()}
        {trip.completed_at && ` · Llegó ${new Date(trip.completed_at).toLocaleString()}`}
      </p>
      <div className="mt-2 flex items-center gap-4">
        <AmountEditor trip={trip} />
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-sm text-slate-500 hover:text-slate-900 hover:underline"
        >
          {expanded ? "Ocultar carros" : "Ver carros"}
        </button>
      </div>
      {expanded && <TripCarsPanel tripId={trip.id} canAdd canDelete />}
    </li>
  );
}

export default function TripsSection() {
  const { data: trips, isLoading } = useQuery({
    queryKey: ["trips"],
    queryFn: async () => (await apiClient.get("/trips")).data,
  });
  const driverNames = useLookup(["drivers"], "/drivers", "full_name");
  const truckPlates = useLookup(["trucks"], "/trucks", "plate");
  const zoneNames = useLookup(["zones"], "/zones", "name");

  return (
    <Card title="Viajes">
      {isLoading ? (
        <p className="text-sm text-slate-400">Cargando...</p>
      ) : trips?.length ? (
        <ul className="divide-y divide-slate-100">
          {trips.map((trip) => (
            <TripRow
              key={trip.id}
              trip={trip}
              driverNames={driverNames}
              truckPlates={truckPlates}
              zoneNames={zoneNames}
            />
          ))}
        </ul>
      ) : (
        <EmptyState>No hay viajes registrados todavía.</EmptyState>
      )}
    </Card>
  );
}
