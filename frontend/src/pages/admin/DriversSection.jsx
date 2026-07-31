import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Button, Card, EmptyState, ErrorText, Select } from "../../components/ui";

export default function DriversSection() {
  const queryClient = useQueryClient();
  const [profileId, setProfileId] = useState("");
  const [error, setError] = useState("");

  const { data: drivers, isLoading } = useQuery({
    queryKey: ["drivers"],
    queryFn: async () => (await apiClient.get("/drivers")).data,
  });

  const { data: profiles } = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await apiClient.get("/profiles")).data,
  });

  const eligibleProfiles = (profiles ?? []).filter(
    (p) => p.role === "driver" && !(drivers ?? []).some((d) => d.profile_id === p.id),
  );

  const createDriver = useMutation({
    mutationFn: async ({ profile_id, full_name }) =>
      (await apiClient.post("/drivers", { profile_id, full_name })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      setProfileId("");
      setError("");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "Error al crear el chofer"),
  });

  const deleteDriver = useMutation({
    mutationFn: async (id) => apiClient.delete(`/drivers/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["drivers"] }),
  });

  return (
    <div className="space-y-6">
      <Card title="Nuevo chofer">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const selected = eligibleProfiles.find((p) => p.id === profileId);
            createDriver.mutate({ profile_id: profileId, full_name: selected?.full_name ?? "" });
          }}
          className="flex flex-col gap-2 sm:flex-row"
        >
          <Select value={profileId} onChange={(e) => setProfileId(e.target.value)} required>
            <option value="" disabled>
              Seleccionar usuario con rol "driver"
            </option>
            {eligibleProfiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name} ({p.email})
              </option>
            ))}
          </Select>
          <Button type="submit" disabled={createDriver.isPending}>
            Crear
          </Button>
        </form>
        {eligibleProfiles.length === 0 && (
          <p className="mt-2 text-xs text-slate-400">
            No hay usuarios con rol "driver" sin registro de chofer. Asigná el rol desde la pestaña
            Usuarios primero.
          </p>
        )}
        <div className="mt-2">
          <ErrorText>{error}</ErrorText>
        </div>
      </Card>

      <Card title="Choferes">
        {isLoading ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : drivers?.length ? (
          <ul className="divide-y divide-slate-100">
            {drivers.map((driver) => (
              <li key={driver.id} className="flex items-center justify-between py-3">
                <span className="text-sm text-slate-900">{driver.full_name}</span>
                <Button variant="danger" onClick={() => deleteDriver.mutate(driver.id)}>
                  Eliminar
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>No hay choferes registrados todavía.</EmptyState>
        )}
      </Card>
    </div>
  );
}
