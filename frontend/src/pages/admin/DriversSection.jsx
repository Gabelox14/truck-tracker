import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import {
  Badge,
  Button,
  Card,
  ConfirmButton,
  EmptyState,
  ErrorText,
  Input,
  Select,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

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
      <Card
        title={
          reset
            ? `Nueva contraseña de ${driver.full_name}`
            : `Acceso de ${driver.full_name}`
        }
      >
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-slate-500">Correo</dt>
          <dd className="break-all font-mono text-base text-slate-900">
            {driver.email}
          </dd>
          <dt className="text-slate-500">Contraseña</dt>
          <dd className="font-mono text-base text-slate-900">{password}</dd>
        </dl>
        <p className="mt-3 text-sm text-slate-500">
          Pásaselos al chofer ahora: la contraseña no se vuelve a mostrar. Si se
          pierde, genera otra con “Nueva contraseña”.
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

function NewDriverCard({ onCreated }) {
  const [fullName, setFullName] = useState("");
  const [cedula, setCedula] = useState("");
  const [error, setError] = useState("");
  const queryClient = useQueryClient();

  const create = useMutation({
    mutationFn: async () =>
      (
        await apiClient.post("/drivers/accounts", {
          full_name: fullName,
          cedula: cedula || null,
        })
      ).data,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      setFullName("");
      setCedula("");
      setError("");
      onCreated(data);
    },
    onError: (err) =>
      setError(err.response?.data?.detail ?? "No se pudo crear el chofer"),
  });

  return (
    <Card title="Nuevo chofer">
      <p className="text-sm text-slate-500">
        El sistema le crea el correo y la contraseña para que solo entre.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
        className="mt-3 flex flex-col gap-2 sm:flex-row"
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
          className="sm:!w-48"
        />
        <Button type="submit" disabled={create.isPending} className="shrink-0">
          {create.isPending ? "Creando…" : "Crear chofer"}
        </Button>
      </form>
      <div className="mt-2">
        <ErrorText>{error}</ErrorText>
      </div>
    </Card>
  );
}

// Choferes que se registraron solos con su email y tienen el rol "driver".
function LinkProfileForm({ drivers }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [profileId, setProfileId] = useState("");
  const [error, setError] = useState("");

  const { data: profiles } = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await apiClient.get("/profiles")).data,
  });
  const eligible = (profiles ?? []).filter(
    (p) =>
      p.role === "driver" &&
      !(drivers ?? []).some((d) => d.profile_id === p.id),
  );

  const link = useMutation({
    mutationFn: async ({ profile_id, full_name }) =>
      (await apiClient.post("/drivers", { profile_id, full_name })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      setProfileId("");
      setError("");
      showToast("Chofer vinculado");
    },
    onError: (err) =>
      setError(err.response?.data?.detail ?? "No se pudo vincular el usuario"),
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
          });
        }}
        className="mt-2 flex flex-col gap-2 sm:flex-row"
      >
        <Select
          value={profileId}
          onChange={(e) => setProfileId(e.target.value)}
          aria-label="Usuario registrado"
          required
        >
          <option value="" disabled>
            Seleccionar usuario
          </option>
          {eligible.map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name} ({p.email})
            </option>
          ))}
        </Select>
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

  const { data: drivers, isLoading } = useQuery({
    queryKey: ["drivers"],
    queryFn: async () => (await apiClient.get("/drivers")).data,
  });

  const deleteDriver = useMutation({
    mutationFn: async (id) => apiClient.delete(`/drivers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      showToast("Chofer eliminado");
    },
    onError: (err) =>
      showToast(
        err.response?.data?.detail ?? "No se pudo eliminar el chofer",
        "error",
      ),
  });

  const toggleActive = useMutation({
    mutationFn: async ({ id, active }) =>
      (await apiClient.patch(`/drivers/${id}`, { active })).data,
    onSuccess: (_data, { active }) => {
      queryClient.invalidateQueries({ queryKey: ["drivers"] });
      showToast(active ? "Chofer reactivado" : "Chofer desactivado");
    },
    onError: (err) =>
      showToast(
        err.response?.data?.detail ?? "No se pudo actualizar el chofer",
        "error",
      ),
  });

  const resetPassword = useMutation({
    mutationFn: async (id) =>
      (await apiClient.post(`/drivers/${id}/password`)).data,
    onSuccess: (data) => setCredentials({ ...data, reset: true }),
    onError: (err) =>
      showToast(
        err.response?.data?.detail ?? "No se pudo cambiar la contraseña",
        "error",
      ),
  });

  return (
    <div className="space-y-6">
      {credentials && (
        <CredentialsCard
          credentials={credentials}
          onClose={() => setCredentials(null)}
        />
      )}
      {isAdmin && <NewDriverCard onCreated={setCredentials} />}

      <Card title="Choferes">
        {isLoading ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : drivers?.length ? (
          <ul className="divide-y divide-slate-100">
            {drivers.map((driver) => (
              <li
                key={driver.id}
                className="flex flex-wrap items-center justify-between gap-2 py-3"
              >
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm text-slate-900">
                    {driver.full_name}
                    {!driver.active && <Badge>Inactivo</Badge>}
                  </p>
                  <p className="truncate text-xs text-slate-400">
                    {driver.email}
                  </p>
                </div>
                <span className="flex flex-wrap items-center gap-2">
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
                    onClick={() =>
                      toggleActive.mutate({
                        id: driver.id,
                        active: !driver.active,
                      })
                    }
                  >
                    {driver.active ? "Desactivar" : "Reactivar"}
                  </Button>
                  {(isAdmin || !driver.username) && (
                    <ConfirmButton
                      pending={deleteDriver.isPending}
                      onConfirm={() => deleteDriver.mutate(driver.id)}
                    />
                  )}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>No hay choferes registrados todavía.</EmptyState>
        )}
        <LinkProfileForm drivers={drivers} />
      </Card>
    </div>
  );
}
