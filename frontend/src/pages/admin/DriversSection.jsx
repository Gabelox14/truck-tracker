import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Badge, Button, Card, ConfirmButton, EmptyState, ErrorText, Input, Select } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

const DRIVER_TYPES = [
  { value: "fijo", label: "Fijo" },
  { value: "suplente", label: "Suplente" },
  { value: "tercero", label: "Tercero" },
];
const typeLabel = (value) => DRIVER_TYPES.find((t) => t.value === value)?.label;

// El código interno (M01) solo le llega al admin; los demás ven la placa.
const truckLabel = (truck) => (truck ? (truck.code ? `${truck.code} · ${truck.plate}` : truck.plate) : null);

// Camiones sin chofer activo (más el del propio chofer, si se está editando).
function freeTrucks(trucks, drivers, driver = null) {
  const taken = new Set(
    (drivers ?? []).filter((d) => d.active && d.truck_id && d.id !== driver?.id).map((d) => d.truck_id),
  );
  return (trucks ?? []).filter((t) => !taken.has(t.id));
}

function TruckSelect({ trucks, value, onChange }) {
  return (
    <Select value={value} onChange={(e) => onChange(e.target.value)} aria-label="Camión" required>
      <option value="" disabled>
        {trucks.length ? "Camión" : "No hay camiones libres"}
      </option>
      {trucks.map((t) => (
        <option key={t.id} value={t.id}>
          {truckLabel(t)}
        </option>
      ))}
    </Select>
  );
}

function TypeSelect({ value, onChange }) {
  return (
    <Select value={value} onChange={(e) => onChange(e.target.value)} aria-label="Tipo de chofer" required>
      <option value="" disabled>
        Tipo de chofer
      </option>
      {DRIVER_TYPES.map((t) => (
        <option key={t.value} value={t.value}>
          {t.label}
        </option>
      ))}
    </Select>
  );
}

// Correo y contraseña recién generados: la contraseña se muestra una sola vez.
function CredentialsCard({ credentials, onClose }) {
  const { showToast } = useToast();
  const { driver, password, reset } = credentials;
  const message = `Full Soluciones — acceso de ${driver.full_name}\nEntrar en: ${window.location.origin}\nCorreo: ${driver.email}\nContraseña: ${password}`;

  // "Nueva contraseña" se pide desde la lista, más abajo: traer la tarjeta a la vista.
  const ref = useRef(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [password]);

  return (
    <div ref={ref} role="status" aria-live="polite">
      <Card title={reset ? `Nueva contraseña de ${driver.full_name}` : `Acceso de ${driver.full_name}`}>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-slate-500">Correo</dt>
          <dd className="break-all font-mono text-base text-slate-900">{driver.email}</dd>
          <dt className="text-slate-500">Contraseña</dt>
          <dd className="font-mono text-base text-slate-900">{password}</dd>
        </dl>
        <p className="mt-3 text-sm text-slate-500">
          Pásaselos al chofer ahora: la contraseña no se vuelve a mostrar. Si se pierde, genera otra con “Nueva
          contraseña”.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(message);
                showToast("Acceso copiado");
              } catch {
                showToast("No se pudo copiar; anótalo a mano", "error");
              }
            }}
          >
            Copiar para enviar
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Listo
          </Button>
        </div>
      </Card>
    </div>
  );
}

function NewDriverCard({ trucks, drivers, onCreated }) {
  const [fullName, setFullName] = useState("");
  const [truckId, setTruckId] = useState("");
  const [driverType, setDriverType] = useState("");
  const [cedula, setCedula] = useState("");
  const [error, setError] = useState("");
  const queryClient = useQueryClient();
  const available = freeTrucks(trucks, drivers);

  const create = useMutation({
    mutationFn: async () =>
      (
        await apiClient.post("/drivers/accounts", {
          full_name: fullName,
          truck_id: truckId,
          driver_type: driverType,
          cedula: cedula || null,
        })
      ).data,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      setFullName("");
      setTruckId("");
      setDriverType("");
      setCedula("");
      setError("");
      onCreated(data);
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo crear el chofer"),
  });

  return (
    <Card title="Nuevo chofer">
      <p className="text-sm text-slate-500">
        El sistema le crea el correo y la contraseña para que solo entre. Cada camión lleva un solo chofer activo.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
        className="mt-3 grid gap-2 sm:grid-cols-2"
      >
        <Input
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Nombre del chofer"
          aria-label="Nombre del chofer"
          autoComplete="off"
          required
        />
        <Input
          value={cedula}
          onChange={(e) => setCedula(e.target.value)}
          placeholder="Cédula (opcional)"
          aria-label="Cédula (opcional)"
          autoComplete="off"
        />
        <TruckSelect trucks={available} value={truckId} onChange={setTruckId} />
        <TypeSelect value={driverType} onChange={setDriverType} />
        <div className="sm:col-span-2">
          <Button type="submit" disabled={create.isPending || available.length === 0}>
            {create.isPending ? "Creando…" : "Crear chofer"}
          </Button>
        </div>
      </form>
      {available.length === 0 && (
        <p className="mt-2 text-xs text-slate-400">
          Todos los camiones tienen chofer. Crea un camión o desactiva al chofer que tiene el que necesitas.
        </p>
      )}
      <div className="mt-2">
        <ErrorText>{error}</ErrorText>
      </div>
    </Card>
  );
}

// Solo admin: cambiar el camión (a uno libre) y el tipo.
function AssignmentForm({ driver, trucks, drivers, onDone }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [truckId, setTruckId] = useState(driver.truck_id ?? "");
  const [driverType, setDriverType] = useState(driver.driver_type ?? "");
  const [error, setError] = useState("");

  const save = useMutation({
    mutationFn: async () =>
      (await apiClient.patch(`/drivers/${driver.id}`, { truck_id: truckId, driver_type: driverType })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      showToast("Chofer actualizado");
      onDone();
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo actualizar el chofer"),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
      className="mt-2 w-full space-y-2"
    >
      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto_auto]">
        <TruckSelect trucks={freeTrucks(trucks, drivers, driver)} value={truckId} onChange={setTruckId} />
        <TypeSelect value={driverType} onChange={setDriverType} />
        <Button type="submit" disabled={save.isPending}>
          Guardar
        </Button>
        <Button variant="ghost" type="button" onClick={onDone}>
          Cancelar
        </Button>
      </div>
      <ErrorText>{error}</ErrorText>
    </form>
  );
}

// Choferes que se registraron solos con su email y tienen el rol "driver".
function LinkProfileForm({ trucks, drivers }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [profileId, setProfileId] = useState("");
  const [truckId, setTruckId] = useState("");
  const [driverType, setDriverType] = useState("");
  const [error, setError] = useState("");

  const { data: profiles } = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await apiClient.get("/profiles")).data,
  });
  const eligible = (profiles ?? []).filter(
    (p) => p.role === "driver" && !(drivers ?? []).some((d) => d.profile_id === p.id),
  );

  const link = useMutation({
    mutationFn: async (body) => (await apiClient.post("/drivers", body)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      setProfileId("");
      setTruckId("");
      setDriverType("");
      setError("");
      showToast("Chofer vinculado");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo vincular el usuario"),
  });

  if (eligible.length === 0) return null;

  return (
    <details className="mt-4 border-t border-slate-100 pt-3">
      <summary className="cursor-pointer text-xs text-slate-400">
        Vincular un usuario que se registró con su email ({eligible.length})
      </summary>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const selected = eligible.find((p) => p.id === profileId);
          link.mutate({
            profile_id: profileId,
            full_name: selected?.full_name ?? "",
            truck_id: truckId,
            driver_type: driverType,
          });
        }}
        className="mt-2 grid gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]"
      >
        <Select value={profileId} onChange={(e) => setProfileId(e.target.value)} aria-label="Usuario registrado" required>
          <option value="" disabled>
            Seleccionar usuario
          </option>
          {eligible.map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name} ({p.email})
            </option>
          ))}
        </Select>
        <TruckSelect trucks={freeTrucks(trucks, drivers)} value={truckId} onChange={setTruckId} />
        <TypeSelect value={driverType} onChange={setDriverType} />
        <Button type="submit" variant="ghost" disabled={link.isPending}>
          Vincular
        </Button>
      </form>
      <ErrorText>{error}</ErrorText>
    </details>
  );
}

export default function DriversSection() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { profile } = useAuth();
  const isAdmin = profile?.role === "admin";
  const [credentials, setCredentials] = useState(null);
  const [editingId, setEditingId] = useState(null);

  const { data: drivers, isLoading } = useQuery({
    queryKey: ["drivers"],
    queryFn: async () => (await apiClient.get("/drivers")).data,
  });
  const { data: trucks } = useQuery({
    queryKey: ["trucks"],
    queryFn: async () => (await apiClient.get("/trucks")).data,
  });
  const truckById = (id) => (trucks ?? []).find((t) => t.id === id);

  const deleteDriver = useMutation({
    mutationFn: async (id) => apiClient.delete(`/drivers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      showToast("Chofer eliminado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo eliminar el chofer", "error"),
  });

  const toggleActive = useMutation({
    mutationFn: async ({ id, active }) => (await apiClient.patch(`/drivers/${id}`, { active })).data,
    onSuccess: (_data, { active }) => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      showToast(active ? "Chofer reactivado" : "Chofer desactivado: su camión quedó libre");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo actualizar el chofer", "error"),
  });

  const resetPassword = useMutation({
    mutationFn: async (id) => (await apiClient.post(`/drivers/${id}/password`)).data,
    onSuccess: (data) => setCredentials({ ...data, reset: true }),
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo cambiar la contraseña", "error"),
  });

  return (
    <div className="space-y-6">
      {credentials && <CredentialsCard credentials={credentials} onClose={() => setCredentials(null)} />}
      {isAdmin && <NewDriverCard trucks={trucks} drivers={drivers} onCreated={setCredentials} />}

      <Card title="Choferes">
        {isLoading ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : drivers?.length ? (
          <ul className="divide-y divide-slate-100">
            {drivers.map((driver) => {
              const truck = truckById(driver.truck_id);
              return (
                <li key={driver.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-center gap-2 text-sm text-slate-900">
                      {driver.full_name}
                      {isAdmin && driver.driver_type && <Badge>{typeLabel(driver.driver_type)}</Badge>}
                      {!driver.active && <Badge>Inactivo</Badge>}
                    </p>
                    <p className="truncate text-xs text-slate-400">
                      {driver.active
                        ? (truckLabel(truck) ?? "Sin camión asignado")
                        : truck
                          ? `Último camión: ${truckLabel(truck)}`
                          : "Sin camión"}{" "}
                      ·{" "}
                      {driver.email}
                    </p>
                  </div>
                  <span className="flex flex-wrap items-center gap-2">
                    {isAdmin && (
                      <Button variant="ghost" onClick={() => setEditingId(editingId === driver.id ? null : driver.id)}>
                        Camión y tipo
                      </Button>
                    )}
                    {isAdmin && driver.username && (
                      <Button
                        variant="ghost"
                        disabled={resetPassword.isPending}
                        onClick={() => {
                          if (
                            window.confirm(
                              `¿Generar una contraseña nueva para ${driver.full_name}? La actual deja de servir.`,
                            )
                          ) {
                            resetPassword.mutate(driver.id);
                          }
                        }}
                      >
                        Nueva contraseña
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      disabled={toggleActive.isPending}
                      onClick={() => toggleActive.mutate({ id: driver.id, active: !driver.active })}
                    >
                      {driver.active ? "Desactivar" : "Reactivar"}
                    </Button>
                    {(isAdmin || !driver.username) && (
                      <ConfirmButton pending={deleteDriver.isPending} onConfirm={() => deleteDriver.mutate(driver.id)} />
                    )}
                  </span>
                  {editingId === driver.id && (
                    <AssignmentForm
                      driver={driver}
                      trucks={trucks}
                      drivers={drivers}
                      onDone={() => setEditingId(null)}
                    />
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <EmptyState>No hay choferes registrados todavía.</EmptyState>
        )}
        {isAdmin && <LinkProfileForm trucks={trucks} drivers={drivers} />}
      </Card>
    </div>
  );
}
