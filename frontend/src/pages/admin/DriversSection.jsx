import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Badge, Button, Card, ConfirmButton, EmptyState, ErrorText, Select } from "../../components/ui";
import { useToast } from "../../context/ToastContext";

export default function DriversSection() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
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
      showToast("Chofer creado");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "Error al crear el chofer"),
  });

  const deleteDriver = useMutation({
    mutationFn: async (id) => apiClient.delete(`/drivers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      showToast("Chofer eliminado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo eliminar el chofer", "error"),
  });

  const toggleActive = useMutation({
    mutationFn: async ({ id, active }) => (await apiClient.patch(`/drivers/${id}`, { active })).data,
    onSuccess: (_data, { active }) => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      showToast(active ? "Chofer reactivado" : "Chofer desactivado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo actualizar el chofer", "error"),
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
          <Select
            value={profileId}
            onChange={(e) => setProfileId(e.target.value)}
            aria-label="Usuario con rol chofer"
            required
          >
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
              <li key={driver.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <span className="flex items-center gap-2 text-sm text-slate-900">
                  {driver.full_name}
                  {!driver.active && <Badge>Inactivo</Badge>}
                </span>
                <span className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    disabled={toggleActive.isPending}
                    onClick={() => toggleActive.mutate({ id: driver.id, active: !driver.active })}
                  >
                    {driver.active ? "Desactivar" : "Reactivar"}
                  </Button>
                  <ConfirmButton
                    pending={deleteDriver.isPending}
                    onConfirm={() => deleteDriver.mutate(driver.id)}
                  />
                </span>
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
