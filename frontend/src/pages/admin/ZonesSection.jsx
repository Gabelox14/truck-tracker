import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Button, Card, ConfirmButton, EmptyState, ErrorText, Input } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

export default function ZonesSection() {
  const { profile } = useAuth();
  const isAdmin = profile?.role === "admin";
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const { data: zones, isLoading } = useQuery({
    queryKey: ["zones"],
    queryFn: async () => (await apiClient.get("/zones")).data,
  });

  const createZone = useMutation({
    mutationFn: async (name) => (await apiClient.post("/zones", { name })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      setName("");
      setError("");
      showToast("Zona creada");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "Error al crear la zona"),
  });

  const deleteZone = useMutation({
    mutationFn: async (id) => apiClient.delete(`/zones/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      showToast("Zona eliminada");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo eliminar la zona", "error"),
  });

  return (
    <div className="space-y-6">
      {isAdmin && (
        <Card title="Nueva zona">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createZone.mutate(name);
            }}
            className="flex flex-col gap-2 sm:flex-row"
          >
            <Input
              placeholder="Nombre de la zona (ej: Bodega Central)"
              aria-label="Nombre de la zona"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Button type="submit" disabled={createZone.isPending}>
              Crear
            </Button>
          </form>
          <div className="mt-2">
            <ErrorText>{error}</ErrorText>
          </div>
        </Card>
      )}

      <Card title="Zonas">
        {isLoading ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : zones?.length ? (
          <ul className="divide-y divide-slate-100">
            {zones.map((zone) => (
              <li key={zone.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <span className="text-sm text-slate-900">{zone.name}</span>
                {isAdmin && (
                  <ConfirmButton
                    pending={deleteZone.isPending}
                    onConfirm={() => deleteZone.mutate(zone.id)}
                  />
                )}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>No hay zonas creadas todavía.</EmptyState>
        )}
      </Card>
    </div>
  );
}
