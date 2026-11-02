import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../lib/apiClient";
import { formatMoney } from "../lib/formatMoney";
import { openIntakeFile } from "../lib/intake";
import { useToast } from "../context/ToastContext";
import { Badge, Button, ErrorText, Input, ReviewBadge, ReviewNotes, Select } from "./ui";

function RemoveCarButton({ onConfirm, pending }) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <span className="inline-flex items-center gap-2 text-xs" role="status" aria-live="polite">
        <span className="text-slate-500">¿Quitar?</span>
        <button
          type="button"
          disabled={pending}
          onClick={() => {
            onConfirm();
            setConfirming(false);
          }}
          className="font-medium text-red-600 hover:underline"
        >
          Sí
        </button>
        <button type="button" onClick={() => setConfirming(false)} className="text-slate-500 hover:underline">
          No
        </button>
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setConfirming(true)}
      className="text-xs text-red-600 hover:underline"
    >
      Quitar
    </button>
  );
}

function vinHint(car) {
  if (!car.vin) return null;
  if (!car.vin_valid) return "no es un VIN de 17 caracteres";
  return car.check_digit_ok ? "VIN válido" : "el dígito verificador no cuadra";
}

function CarFields({ values, onChange }) {
  const field = (key) => ({
    value: values[key] ?? "",
    onChange: (e) => onChange({ ...values, [key]: e.target.value }),
  });
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-5">
      <Input placeholder="Marca" aria-label="Marca" required {...field("brand")} />
      <Input placeholder="VIN" aria-label="VIN" className="font-mono sm:col-span-2" {...field("vin")} />
      <Input placeholder="Modelo" aria-label="Modelo" {...field("model")} />
      <Input placeholder="Año" aria-label="Año" type="number" min="1900" max="2100" {...field("model_year")} />
      <Select aria-label="Clase de vehículo" {...field("vehicle_class")}>
        <option value="">Clase según el modelo</option>
        <option value="liviano">Liviano</option>
        <option value="carga">Carga</option>
      </Select>
      <Input
        placeholder="Monto (vacío = tarifa)"
        aria-label="Monto del vehículo"
        type="number"
        min="0"
        step="500"
        className="sm:col-span-2"
        {...field("amount")}
      />
    </div>
  );
}

function toPayload(values) {
  const payload = {
    brand: values.brand?.trim() || null,
    vin: values.vin?.trim() || null,
    model: values.model?.trim() || null,
    model_year: values.model_year ? Number(values.model_year) : null,
  };
  if (values.vehicle_class) payload.vehicle_class = values.vehicle_class;
  if (values.amount !== undefined && values.amount !== "") payload.amount = Number(values.amount);
  return payload;
}

function CarRow({ car, tripId, currency, canEdit, canDelete, onRemove, removing }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState({});

  const update = useMutation({
    mutationFn: async (payload) => (await apiClient.patch(`/trips/${tripId}/cars/${car.id}`, payload)).data,
    onSuccess: (_data, payload) => {
      queryClient.invalidateQueries({ queryKey: ["trip-cars", tripId] });
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      queryClient.invalidateQueries({ queryKey: ["trip", tripId] });
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      setEditing(false);
      showToast(payload.review_status === "confirmed" ? "Carro confirmado" : "Carro corregido");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo guardar el carro", "error"),
  });

  function openPhoto() {
    openIntakeFile(car.photo_file_id).catch(() => showToast("No se pudo abrir la foto", "error"));
  }

  const vehicle = [car.brand ?? car.make_from_photo, car.model, car.model_year].filter(Boolean).join(" ");
  const hint = vinHint(car);

  return (
    <li className="py-2">
      <div className="flex flex-wrap items-start justify-between gap-2 text-sm">
        <div className="min-w-0 space-y-0.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-900">{vehicle || "Vehículo sin marca"}</span>
            {car.color && <span className="text-xs text-slate-400">{car.color}</span>}
            {car.vehicle_class === "carga" && <Badge>Carga</Badge>}
            <ReviewBadge status={car.review_status} />
          </div>
          {canEdit && (
            <p className="text-xs text-slate-500">
              {car.amount != null ? formatMoney(car.amount, currency) : "Sin monto (la ruta no tiene tarifa)"}
            </p>
          )}
          {car.vin && (
            <p className="break-all font-mono text-xs text-slate-600">
              {car.vin}
              {hint && <span className="font-sans text-slate-400"> · {hint}</span>}
            </p>
          )}
          {car.review_status === "needs_review" && <ReviewNotes notes={car.review_notes} />}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-3 text-xs">
          {car.photo_file_id && (
            <button type="button" onClick={openPhoto} className="text-slate-600 hover:text-slate-900 hover:underline">
              Ver foto
            </button>
          )}
          {canEdit && car.review_status === "needs_review" && (
            <button
              type="button"
              disabled={update.isPending}
              onClick={() => update.mutate({ review_status: "confirmed" })}
              className="font-medium text-slate-900 hover:underline"
            >
              Confirmar
            </button>
          )}
          {canEdit && (
            <button
              type="button"
              onClick={() => {
                setValues({
                  brand: car.brand ?? car.make_from_photo ?? "",
                  vin: car.vin ?? "",
                  model: car.model ?? "",
                  model_year: car.model_year ?? "",
                  vehicle_class: car.vehicle_class ?? "",
                  amount: car.amount ?? "",
                });
                setEditing((v) => !v);
              }}
              className="text-slate-600 hover:text-slate-900 hover:underline"
            >
              {editing ? "Cancelar" : "Corregir"}
            </button>
          )}
          {canDelete && <RemoveCarButton pending={removing} onConfirm={() => onRemove(car.id)} />}
        </div>
      </div>
      {editing && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            update.mutate({ ...toPayload(values), review_status: "confirmed" });
          }}
          className="mt-2 space-y-2"
        >
          <CarFields values={values} onChange={setValues} />
          <Button type="submit" disabled={update.isPending}>
            Guardar y confirmar
          </Button>
        </form>
      )}
    </li>
  );
}

export function TripCarsPanel({ tripId, currency = "CRC", canAdd = false, canDelete = false, canEdit = false }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [values, setValues] = useState({});
  const [error, setError] = useState("");

  const { data: cars } = useQuery({
    queryKey: ["trip-cars", tripId],
    queryFn: async () => (await apiClient.get(`/trips/${tripId}/cars`)).data,
  });

  const addCar = useMutation({
    mutationFn: async (payload) => (await apiClient.post(`/trips/${tripId}/cars`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trip-cars", tripId] });
      queryClient.invalidateQueries({ queryKey: ["trip", tripId] });
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      setValues({});
      setError("");
      showToast("Carro agregado");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo agregar el carro"),
  });

  const removeCar = useMutation({
    mutationFn: async (carId) => apiClient.delete(`/trips/${tripId}/cars/${carId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trip-cars", tripId] });
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      queryClient.invalidateQueries({ queryKey: ["trip", tripId] });
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      showToast("Carro quitado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo quitar el carro", "error"),
  });

  return (
    <div className="mt-4 border-t border-slate-100 pt-4">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Carros transportados</p>

      {cars?.length ? (
        <ul className="divide-y divide-slate-100">
          {cars.map((car) => (
            <CarRow
              key={car.id}
              car={car}
              tripId={tripId}
              currency={currency}
              canEdit={canEdit}
              canDelete={canDelete}
              onRemove={(carId) => removeCar.mutate(carId)}
              removing={removeCar.isPending}
            />
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-400">Sin carros agregados.</p>
      )}

      {canAdd && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError("");
            addCar.mutate(toPayload(values));
          }}
          className="mt-3 space-y-2"
        >
          <p className="text-xs text-slate-400">Agregar a mano (sin foto):</p>
          <CarFields values={values} onChange={setValues} />
          <Button type="submit" disabled={addCar.isPending}>
            Agregar carro
          </Button>
        </form>
      )}
      <ErrorText>{error}</ErrorText>
    </div>
  );
}
