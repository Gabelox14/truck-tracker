import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Button, Card, ConfirmButton, EmptyState, ErrorText, Input } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

// Datos que solo maneja el admin (código interno y ficha del Registro Nacional).
const DETAIL_FIELDS = [
  { key: "code", label: "Código (ej: M01)" },
  { key: "brand", label: "Marca" },
  { key: "model", label: "Modelo / estilo" },
  { key: "year", label: "Año", type: "number" },
  { key: "body_type", label: "Carrocería" },
  { key: "traction", label: "Tracción" },
  { key: "color", label: "Color" },
  { key: "vin", label: "VIN / chasis" },
];
const EMPTY = Object.fromEntries([["plate", ""], ...DETAIL_FIELDS.map((f) => [f.key, ""])]);

function toPayload(values, isAdmin) {
  if (!isAdmin) return { plate: values.plate.trim() };
  const payload = { plate: values.plate.trim() };
  for (const { key } of DETAIL_FIELDS) {
    const value = String(values[key] ?? "").trim();
    payload[key] = value === "" ? null : key === "year" ? Number(value) : value;
  }
  return payload;
}

function TruckFields({ values, onChange, isAdmin }) {
  const set = (key) => (e) => onChange({ ...values, [key]: e.target.value });
  return (
    <div className="grid gap-2 sm:grid-cols-3">
      <Input placeholder="Placa (ej: C 177685)" aria-label="Placa" value={values.plate} onChange={set("plate")} required />
      {isAdmin &&
        DETAIL_FIELDS.map((f) => (
          <Input
            key={f.key}
            type={f.type ?? "text"}
            placeholder={f.label}
            aria-label={f.label}
            value={values[f.key] ?? ""}
            onChange={set(f.key)}
          />
        ))}
    </div>
  );
}

function EditTruckForm({ truck, onDone }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [values, setValues] = useState(() =>
    Object.fromEntries(Object.keys(EMPTY).map((k) => [k, truck[k] ?? ""])),
  );
  const [error, setError] = useState("");

  const save = useMutation({
    mutationFn: async () => (await apiClient.patch(`/trucks/${truck.id}`, toPayload(values, true))).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trucks"] });
      showToast("Camión actualizado");
      onDone();
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo guardar el camión"),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
      className="mt-2 w-full space-y-2"
    >
      <TruckFields values={values} onChange={setValues} isAdmin />
      <div className="flex gap-2">
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

export default function TrucksSection() {
  const { profile } = useAuth();
  const isAdmin = profile?.role === "admin";
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [values, setValues] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  const { data: trucks, isLoading } = useQuery({
    queryKey: ["trucks"],
    queryFn: async () => (await apiClient.get("/trucks")).data,
  });
  const sorted = [...(trucks ?? [])].sort((a, b) =>
    (a.code ?? a.plate).localeCompare(b.code ?? b.plate, "es", { numeric: true }),
  );

  const createTruck = useMutation({
    mutationFn: async (payload) => (await apiClient.post("/trucks", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trucks"] });
      setValues(EMPTY);
      setError("");
      showToast("Camión creado");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "Error al crear el camión"),
  });

  const deleteTruck = useMutation({
    mutationFn: async (id) => apiClient.delete(`/trucks/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trucks"] });
      showToast("Camión eliminado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo eliminar el camión", "error"),
  });

  return (
    <div className="space-y-6">
      <Card title="Nuevo camión">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createTruck.mutate(toPayload(values, isAdmin));
          }}
          className="space-y-2"
        >
          <TruckFields values={values} onChange={setValues} isAdmin={isAdmin} />
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
        ) : sorted.length ? (
          <ul className="divide-y divide-slate-100">
            {sorted.map((truck) => (
              <li key={truck.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div className="min-w-0">
                  <p className="text-sm text-slate-900">
                    {isAdmin && truck.code && <span className="font-medium">{truck.code} · </span>}
                    {truck.plate}
                  </p>
                  {isAdmin && (
                    <>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {[
                          [truck.brand, truck.model].filter(Boolean).join(" "),
                          truck.year,
                          truck.body_type,
                          truck.traction,
                          truck.color,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                      {truck.vin && <p className="font-mono text-xs text-slate-400">VIN {truck.vin}</p>}
                    </>
                  )}
                </div>
                <span className="flex items-center gap-2">
                  {isAdmin && (
                    <Button variant="ghost" onClick={() => setEditingId(editingId === truck.id ? null : truck.id)}>
                      Editar
                    </Button>
                  )}
                  <ConfirmButton pending={deleteTruck.isPending} onConfirm={() => deleteTruck.mutate(truck.id)} />
                </span>
                {editingId === truck.id && <EditTruckForm truck={truck} onDone={() => setEditingId(null)} />}
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
