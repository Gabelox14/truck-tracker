import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { IntakeUpload } from "../../components/IntakeUpload";
import { Button, Card, ConfirmButton, EmptyState, ErrorText, Input, ReviewNotes, Select } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { apiClient } from "../../lib/apiClient";
import { CURRENCIES, formatMoney } from "../../lib/formatMoney";
import { invalidateIntake, openIntakeFile } from "../../lib/intake";

function useList(queryKey, path) {
  const { data } = useQuery({ queryKey, queryFn: async () => (await apiClient.get(path)).data });
  return data ?? [];
}

function draftSummary(draft) {
  const result = draft.extraction ?? {};
  if (draft.kind === "vin_photo") {
    const vehicle = [result.make ?? result.nhtsa?.make, result.nhtsa?.model ?? result.model].filter(Boolean).join(" ");
    return { title: vehicle || "Foto sin vehículo identificado", detail: result.vin, reasons: result.review_reasons };
  }
  const extraction = result.extraction ?? {};
  const route = [extraction.origin?.normalized, extraction.destination?.normalized].filter(Boolean).join(" → ");
  const cost = result.cost_amount != null ? formatMoney(result.cost_amount, result.cost_currency) : null;
  return {
    title: route || "Nota de voz sin origen ni destino",
    detail: [cost, draft.transcript && `«${draft.transcript}»`].filter(Boolean).join(" · "),
    reasons: result.review_reasons,
  };
}

function CreateTripForm({ draft, drafts, drivers, trucks, zones, onDone }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const result = draft.extraction ?? {};
  const audioDate = result.extraction?.trip_date ?? "";
  const directa = result.extraction?.invoice_type === "directa";
  const [values, setValues] = useState({
    driver_id: result.driver_id ?? "",
    truck_id: result.truck_id ?? "",
    origin_zone_id: result.origin_zone_id ?? "",
    destination_zone_id: result.destination_zone_id ?? "",
    // En directos cada vehículo toma la tarifa de la ruta: el total sale solo.
    amount: result.cost_per_vehicle ? "" : (result.cost_amount ?? ""),
    currency: result.cost_currency ?? "CRC",
    trip_type: directa ? "directo" : "",
    trip_date: audioDate,
    requested_by: result.requested_by ?? "",
  });
  const [extraIds, setExtraIds] = useState([]);
  const [error, setError] = useState("");
  const others = drafts.filter((d) => d.id !== draft.id);
  const set = (key) => (e) => setValues((v) => ({ ...v, [key]: e.target.value }));

  const create = useMutation({
    mutationFn: async (payload) => (await apiClient.post("/intake/drafts/create-trip", payload)).data,
    onSuccess: (trip) => {
      invalidateIntake(queryClient, trip.id);
      showToast("Viaje creado");
      onDone();
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo crear el viaje"),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (values.origin_zone_id === values.destination_zone_id) {
          setError("El destino tiene que ser distinto al origen.");
          return;
        }
        create.mutate({
          file_ids: [draft.id, ...extraIds],
          driver_id: values.driver_id,
          truck_id: values.truck_id || null,
          origin_zone_id: values.origin_zone_id,
          destination_zone_id: values.destination_zone_id,
          amount: values.amount === "" ? null : Number(values.amount),
          currency: values.currency,
          trip_type: values.trip_type || null,
          trip_date: values.trip_date || null,
          requested_by: values.requested_by.trim() || null,
        });
      }}
      className="mt-3 space-y-2 rounded-lg border border-slate-200 p-3"
    >
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <Select
          value={values.driver_id}
          onChange={(e) => {
            // El chofer sale en su camión asignado (el tercero, en su propio vehículo).
            const driver = drivers.find((d) => d.id === e.target.value);
            setValues((v) => ({ ...v, driver_id: e.target.value, truck_id: driver?.truck_id ?? "" }));
          }}
          aria-label="Chofer"
          required
        >
          <option value="" disabled>
            Chofer
          </option>
          {drivers.filter((d) => d.active).map((d) => (
            <option key={d.id} value={d.id}>
              {d.full_name}
            </option>
          ))}
        </Select>
        <Select value={values.truck_id} onChange={set("truck_id")} aria-label="Camión">
          <option value="">Sin camión (tercero)</option>
          {trucks.map((t) => (
            <option key={t.id} value={t.id}>
              {t.plate}
            </option>
          ))}
        </Select>
        <Select value={values.origin_zone_id} onChange={set("origin_zone_id")} aria-label="Salió de" required>
          <option value="" disabled>
            Salió de...
          </option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </Select>
        <Select value={values.destination_zone_id} onChange={set("destination_zone_id")} aria-label="Llegó a" required>
          <option value="" disabled>
            Llegó a...
          </option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </Select>
        <Input
          type="number"
          step="0.01"
          min="0"
          placeholder="Monto total (vacío = tarifas)"
          aria-label="Monto total"
          value={values.amount}
          onChange={set("amount")}
        />
        <Select value={values.currency} onChange={set("currency")} aria-label="Moneda">
          {CURRENCIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </Select>
        <Select value={values.trip_type} onChange={set("trip_type")} aria-label="Tipo de viaje">
          <option value="">Tipo de viaje</option>
          <option value="directo">Directo</option>
          <option value="indirecto">Indirecto</option>
        </Select>
        <Input type="date" aria-label="Fecha del viaje" value={values.trip_date} onChange={set("trip_date")} />
        <Input
          placeholder="Solicitado por"
          aria-label="Solicitado por"
          value={values.requested_by}
          onChange={set("requested_by")}
          className="sm:col-span-2"
        />
      </div>
      {others.length > 0 && (
        <fieldset className="space-y-1">
          <legend className="text-xs text-slate-400">Agregar también al viaje:</legend>
          {others.map((other) => (
            <label key={other.id} className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={extraIds.includes(other.id)}
                onChange={(e) =>
                  setExtraIds((ids) => (e.target.checked ? [...ids, other.id] : ids.filter((id) => id !== other.id)))
                }
              />
              {other.kind === "audio" ? "Nota de voz" : "Foto"}: {draftSummary(other).title}
            </label>
          ))}
        </fieldset>
      )}
      <ErrorText>{error}</ErrorText>
      <Button type="submit" disabled={create.isPending}>
        Crear viaje
      </Button>
    </form>
  );
}

function AttachForm({ draft, trips, truckPlates, zoneNames, onDone }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [tripId, setTripId] = useState("");
  const [error, setError] = useState("");

  const attach = useMutation({
    mutationFn: async () => (await apiClient.post(`/intake/files/${draft.id}/attach`, { trip_id: tripId })).data,
    onSuccess: () => {
      invalidateIntake(queryClient, tripId);
      showToast("Archivo ligado al viaje");
      onDone();
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo ligar el archivo"),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        attach.mutate();
      }}
      className="mt-3 flex flex-col gap-2 sm:flex-row"
    >
      <Select value={tripId} onChange={(e) => setTripId(e.target.value)} aria-label="Viaje" required>
        <option value="" disabled>
          Elegir viaje
        </option>
        {trips.map((t) => (
          <option key={t.id} value={t.id}>
            {new Date(t.started_at).toLocaleDateString()} · {t.truck_id ? (truckPlates[t.truck_id] ?? "?") : "Tercero"} · {zoneNames[t.origin_zone_id] ?? "?"} →{" "}
            {zoneNames[t.destination_zone_id] ?? "?"}
          </option>
        ))}
      </Select>
      <Button type="submit" disabled={attach.isPending}>
        Ligar
      </Button>
      <ErrorText>{error}</ErrorText>
    </form>
  );
}

function DraftRow({ draft, drafts, lookups }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [mode, setMode] = useState(null);
  const summary = draftSummary(draft);

  const discard = useMutation({
    mutationFn: async () => apiClient.delete(`/intake/files/${draft.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      showToast("Borrador descartado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo descartar", "error"),
  });

  const toggle = (next) => setMode((current) => (current === next ? null : next));

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-0.5">
          <p className="text-sm text-slate-900">
            <span className="text-slate-400">{draft.kind === "audio" ? "Nota de voz" : "Foto"} · </span>
            {summary.title}
          </p>
          {summary.detail && <p className="break-all text-xs text-slate-500">{summary.detail}</p>}
          <p className="text-xs text-slate-400">{new Date(draft.created_at).toLocaleString()}</p>
          <ReviewNotes notes={summary.reasons} />
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button
            variant="ghost"
            onClick={() => openIntakeFile(draft.id).catch(() => showToast("No se pudo abrir el archivo", "error"))}
          >
            {draft.kind === "audio" ? "Escuchar" : "Ver foto"}
          </Button>
          <Button variant="ghost" onClick={() => toggle("attach")}>
            Ligar a viaje
          </Button>
          <Button variant="ghost" onClick={() => toggle("create")}>
            Crear viaje
          </Button>
          <ConfirmButton onConfirm={() => discard.mutate()} pending={discard.isPending}>
            Descartar
          </ConfirmButton>
        </div>
      </div>
      {mode === "attach" && <AttachForm draft={draft} onDone={() => setMode(null)} {...lookups} />}
      {mode === "create" && <CreateTripForm draft={draft} drafts={drafts} onDone={() => setMode(null)} {...lookups} />}
    </li>
  );
}

function ConfirmTripButton({ tripId }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const confirm = useMutation({
    mutationFn: async () => (await apiClient.patch(`/trips/${tripId}/review`, {})).data,
    onSuccess: () => {
      invalidateIntake(queryClient, tripId);
      showToast("Viaje confirmado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo confirmar", "error"),
  });
  return (
    <Button onClick={() => confirm.mutate()} disabled={confirm.isPending}>
      Confirmar
    </Button>
  );
}

function ConfirmCarButton({ car }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const confirm = useMutation({
    mutationFn: async () =>
      (await apiClient.patch(`/trips/${car.trip_id}/cars/${car.id}`, { review_status: "confirmed" })).data,
    onSuccess: () => {
      invalidateIntake(queryClient, car.trip_id);
      showToast("Carro confirmado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo confirmar", "error"),
  });
  return (
    <Button onClick={() => confirm.mutate()} disabled={confirm.isPending}>
      Confirmar
    </Button>
  );
}

export default function ReviewSection() {
  const { data: queue, isLoading } = useQuery({
    queryKey: ["review-queue"],
    queryFn: async () => (await apiClient.get("/intake/review-queue")).data,
  });
  const drivers = useList(["drivers"], "/drivers");
  const trucks = useList(["trucks"], "/trucks");
  const zones = useList(["zones"], "/zones");
  const trips = useList(["trips"], "/trips");

  const truckPlates = Object.fromEntries(trucks.map((t) => [t.id, t.plate]));
  const zoneNames = Object.fromEntries(zones.map((z) => [z.id, z.name]));
  const driverNames = Object.fromEntries(drivers.map((d) => [d.id, d.full_name]));
  const lookups = { drivers, trucks, zones, trips, truckPlates, zoneNames };

  if (isLoading) return <p className="text-sm text-slate-400">Cargando...</p>;

  const pendingTrips = queue?.trips ?? [];
  const pendingCars = queue?.cars ?? [];
  const drafts = queue?.drafts ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <IntakeUpload title="Subir fotos o notas de voz recibidas (quedan como borrador)" />
      </Card>

      <Card title={`Viajes por revisar (${pendingTrips.length})`}>
        {pendingTrips.length ? (
          <ul className="divide-y divide-slate-100">
            {pendingTrips.map((trip) => (
              <li key={trip.id} className="flex flex-wrap items-start justify-between gap-2 py-3">
                <div className="min-w-0 space-y-0.5">
                  <p className="text-sm font-medium text-slate-900">
                    {driverNames[trip.driver_id] ?? "Chofer"} · {trip.truck_id ? (truckPlates[trip.truck_id] ?? "Camión") : "Tercero"}
                  </p>
                  <p className="text-sm text-slate-500">
                    {zoneNames[trip.origin_zone_id] ?? "?"} → {zoneNames[trip.destination_zone_id] ?? "?"}
                    {trip.amount != null && ` · ${formatMoney(trip.amount, trip.currency)}`}
                  </p>
                  <ReviewNotes notes={trip.review_notes} />
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Link to={`/viajes/${trip.id}`} className="text-sm text-slate-600 hover:text-slate-900 hover:underline">
                    Abrir
                  </Link>
                  <ConfirmTripButton tripId={trip.id} />
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>No hay viajes por revisar.</EmptyState>
        )}
      </Card>

      <Card title={`Carros por revisar (${pendingCars.length})`}>
        {pendingCars.length ? (
          <ul className="divide-y divide-slate-100">
            {pendingCars.map((car) => (
              <li key={car.id} className="flex flex-wrap items-start justify-between gap-2 py-3">
                <div className="min-w-0 space-y-0.5">
                  <p className="text-sm text-slate-900">
                    {[car.brand ?? car.make_from_photo, car.model, car.model_year].filter(Boolean).join(" ") || "Vehículo sin marca"}
                  </p>
                  {car.vin && <p className="break-all font-mono text-xs text-slate-600">{car.vin}</p>}
                  <ReviewNotes notes={car.review_notes} />
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Link to={`/viajes/${car.trip_id}`} className="text-sm text-slate-600 hover:text-slate-900 hover:underline">
                    Abrir viaje
                  </Link>
                  <ConfirmCarButton car={car} />
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>No hay carros por revisar.</EmptyState>
        )}
      </Card>

      <Card title={`Borradores sin viaje (${drafts.length})`}>
        {drafts.length ? (
          <ul className="divide-y divide-slate-100">
            {drafts.map((draft) => (
              <DraftRow key={draft.id} draft={draft} drafts={drafts} lookups={lookups} />
            ))}
          </ul>
        ) : (
          <EmptyState>No hay fotos ni notas de voz sin viaje.</EmptyState>
        )}
      </Card>
    </div>
  );
}
