import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Badge, Button, Card, EmptyState, Input, Select } from "../../components/ui";
import { TripCarsPanel } from "../../components/TripCarsPanel";
import { useToast } from "../../context/ToastContext";

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
  const { showToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState(trip.amount ?? "");

  const setTripAmount = useMutation({
    mutationFn: async (value) =>
      (await apiClient.patch(`/trips/${trip.id}/amount`, { amount: Number(value) })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      setEditing(false);
      showToast("Monto guardado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo guardar el monto", "error"),
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
          className="!w-24"
          autoFocus
          required
        />
        <Button type="submit" disabled={setTripAmount.isPending}>
          Guardar
        </Button>
        <Button variant="ghost" type="button" onClick={() => setEditing(false)}>
          Cancelar
        </Button>
      </form>
    );
  }

  const hasAmount = trip.amount != null;

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className={`rounded-lg border px-2.5 py-1 text-sm font-medium transition ${
        hasAmount
          ? "border-slate-300 bg-white text-slate-900 hover:border-slate-900"
          : "border-dashed border-slate-300 text-slate-500 hover:border-slate-900 hover:text-slate-900"
      }`}
    >
      {hasAmount ? `$${Number(trip.amount).toFixed(2)}` : "+ Agregar monto"}
    </button>
  );
}

function TripTypeEditor({ trip }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const setTripType = useMutation({
    mutationFn: async (trip_type) => (await apiClient.patch(`/trips/${trip.id}/type`, { trip_type })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      showToast("Tipo de viaje guardado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo guardar el tipo de viaje", "error"),
  });

  return (
    <Select
      value={trip.trip_type ?? ""}
      onChange={(e) => e.target.value && setTripType.mutate(e.target.value)}
      disabled={setTripType.isPending}
      aria-label="Tipo de viaje"
      className="!w-auto"
    >
      <option value="" disabled>
        Tipo de viaje
      </option>
      <option value="directo">Directo</option>
      <option value="indirecto">Indirecto</option>
    </Select>
  );
}

function TripRow({ trip, driverNames, truckPlates, zoneNames }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
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
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <AmountEditor trip={trip} />
        <TripTypeEditor trip={trip} />
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
