import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Button, Card, EmptyState, ErrorText, Input } from "../../components/ui";

export default function TrucksSection() {
  const queryClient = useQueryClient();
  const [plate, setPlate] = useState("");
  const [error, setError] = useState("");

  const { data: trucks, isLoading } = useQuery({
    queryKey: ["trucks"],
    queryFn: async () => (await apiClient.get("/trucks")).data,
  });

  const createTruck = useMutation({
    mutationFn: async (plate) => (await apiClient.post("/trucks", { plate })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trucks"] });
      setPlate("");
      setError("");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "Error al crear el camión"),
  });

  const deleteTruck = useMutation({
    mutationFn: async (id) => apiClient.delete(`/trucks/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["trucks"] }),
  });

  return (
    <div className="space-y-6">
      <Card title="Nuevo camión">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createTruck.mutate(plate);
          }}
          className="flex gap-2"
        >
          <Input
            placeholder="Patente (ej: ABC123)"
            value={plate}
            onChange={(e) => setPlate(e.target.value)}
            required
          />
          <Button type="submit" disabled={createTruck.isPending}>
            Crear
          </Button>
        </form>
        <div className="mt-2">
          <ErrorText>{error}</ErrorText>
        </div>
      </Card>

      <Card title="Camiones">
        {isLoading ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : trucks?.length ? (
          <ul className="divide-y divide-slate-100">
            {trucks.map((truck) => (
              <li key={truck.id} className="flex items-center justify-between py-3">
                <span className="text-sm text-slate-900">{truck.plate}</span>
                <Button variant="danger" onClick={() => deleteTruck.mutate(truck.id)}>
                  Eliminar
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>No hay camiones registrados todavía.</EmptyState>
        )}
      </Card>
    </div>
  );
}
