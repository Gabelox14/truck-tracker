import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, EmptyState, ErrorText, Select } from "../components/ui";
import { apiClient } from "../lib/apiClient";
import { Layout } from "../components/Layout";

export default function DriverPage() {
  const queryClient = useQueryClient();
  const [truckId, setTruckId] = useState("");
  const [originZoneId, setOriginZoneId] = useState("");
  const [destinationZoneId, setDestinationZoneId] = useState("");
  const [error, setError] = useState("");

  const { data: trips, isLoading } = useQuery({
    queryKey: ["my-trips"],
    queryFn: async () => (await apiClient.get("/trips")).data,
  });

  const { data: trucks } = useQuery({
    queryKey: ["trucks"],
    queryFn: async () => (await apiClient.get("/trucks")).data,
  });

  const { data: zones } = useQuery({
    queryKey: ["zones"],
    queryFn: async () => (await apiClient.get("/zones")).data,
  });

  const startTrip = useMutation({
    mutationFn: async (payload) => (await apiClient.post("/trips", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-trips"] });
      setTruckId("");
      setOriginZoneId("");
      setDestinationZoneId("");
      setError("");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo iniciar el viaje"),
  });

  const completeTrip = useMutation({
    mutationFn: async (id) => (await apiClient.post(`/trips/${id}/complete`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-trips"] }),
  });

  const zoneName = (id) => zones?.find((z) => z.id === id)?.name ?? "?";
  const truckPlate = (id) => trucks?.find((t) => t.id === id)?.plate ?? "?";

  const activeTrip = trips?.find((t) => t.status === "in_progress");
  const history = trips?.filter((t) => t.status === "completed") ?? [];

  return (
    <Layout>
      <div className="space-y-6">
        {isLoading ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : activeTrip ? (
          <Card title="Viaje en curso">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-900">
                  {truckPlate(activeTrip.truck_id)}
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  {zoneName(activeTrip.origin_zone_id)} → {zoneName(activeTrip.destination_zone_id)}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Salió {new Date(activeTrip.started_at).toLocaleString()}
                </p>
              </div>
              <Button onClick={() => completeTrip.mutate(activeTrip.id)} disabled={completeTrip.isPending}>
                Marcar como llegado
              </Button>
            </div>
          </Card>
        ) : (
          <Card title="Iniciar viaje">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                startTrip.mutate({
                  truck_id: truckId,
                  origin_zone_id: originZoneId,
                  destination_zone_id: destinationZoneId,
                });
              }}
              className="space-y-3"
            >
              <Select value={truckId} onChange={(e) => setTruckId(e.target.value)} required>
                <option value="" disabled>
                  Camión
                </option>
                {trucks?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.plate}
                  </option>
                ))}
              </Select>
              <Select value={originZoneId} onChange={(e) => setOriginZoneId(e.target.value)} required>
                <option value="" disabled>
                  Salgo de...
                </option>
                {zones?.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </Select>
              <Select
                value={destinationZoneId}
                onChange={(e) => setDestinationZoneId(e.target.value)}
                required
              >
                <option value="" disabled>
                  Voy a...
                </option>
                {zones?.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </Select>
              <ErrorText>{error}</ErrorText>
              <Button type="submit" className="w-full" disabled={startTrip.isPending}>
                Iniciar viaje
              </Button>
            </form>
          </Card>
        )}

        <Card title="Historial">
          {history.length ? (
            <ul className="divide-y divide-slate-100">
              {history.map((trip) => (
                <li key={trip.id} className="py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-900">
                      {zoneName(trip.origin_zone_id)} → {zoneName(trip.destination_zone_id)}
                    </span>
                    <Badge tone="emerald">Completado</Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-400">
                    {new Date(trip.started_at).toLocaleDateString()}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState>Todavía no completaste ningún viaje.</EmptyState>
          )}
        </Card>
      </div>
    </Layout>
  );
}
