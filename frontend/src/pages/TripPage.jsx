import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { IntakeUpload } from "../components/IntakeUpload";
import { Layout } from "../components/Layout";
import { TripCarsPanel } from "../components/TripCarsPanel";
import { Badge, Button, Card, EmptyState, ErrorText, Input, ReviewBadge, ReviewNotes, Select } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { apiClient } from "../lib/apiClient";
import { CURRENCIES, formatMoney } from "../lib/formatMoney";
import { invalidateIntake, openIntakeFile } from "../lib/intake";

const SOURCE_LABEL = { manual: "Registrado en la app", upload: "Creado desde una captura", whatsapp: "Creado desde WhatsApp" };

function useList(queryKey, path, enabled = true) {
  const { data } = useQuery({
    queryKey,
    queryFn: async () => (await apiClient.get(path)).data,
    enabled,
  });
  return data ?? [];
}

function ReviewEditor({ trip, zones }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [correcting, setCorrecting] = useState(false);
  const [values, setValues] = useState({});
  const [error, setError] = useState("");

  const confirm = useMutation({
    mutationFn: async (payload) => (await apiClient.patch(`/trips/${trip.id}/review`, payload)).data,
    onSuccess: () => {
      invalidateIntake(queryClient, trip.id);
      setCorrecting(false);
      setError("");
      showToast("Viaje confirmado");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo confirmar el viaje"),
  });

  function startCorrecting() {
    setValues({
      origin_zone_id: trip.origin_zone_id,
      destination_zone_id: trip.destination_zone_id,
      amount: trip.amount ?? "",
      currency: trip.currency,
      requested_by: trip.requested_by ?? "",
    });
    setCorrecting(true);
  }

  const set = (key) => (e) => setValues((v) => ({ ...v, [key]: e.target.value }));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {trip.review_status === "needs_review" && (
          <Button onClick={() => confirm.mutate({})} disabled={confirm.isPending}>
            Confirmar como está
          </Button>
        )}
        <Button variant="ghost" onClick={() => (correcting ? setCorrecting(false) : startCorrecting())}>
          {correcting ? "Cancelar" : "Corregir datos"}
        </Button>
      </div>
      {correcting && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            confirm.mutate({
              origin_zone_id: values.origin_zone_id,
              destination_zone_id: values.destination_zone_id,
              amount: values.amount === "" ? null : Number(values.amount),
              currency: values.currency,
              requested_by: values.requested_by.trim() || null,
            });
          }}
          className="grid grid-cols-1 gap-2 sm:grid-cols-2"
        >
          <Select value={values.origin_zone_id} onChange={set("origin_zone_id")} aria-label="Salió de">
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                Salió de {z.name}
              </option>
            ))}
          </Select>
          <Select value={values.destination_zone_id} onChange={set("destination_zone_id")} aria-label="Llegó a">
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                Llegó a {z.name}
              </option>
            ))}
          </Select>
          <Input type="number" step="0.01" min="0" placeholder="Monto" aria-label="Monto" value={values.amount} onChange={set("amount")} />
          <Select value={values.currency} onChange={set("currency")} aria-label="Moneda">
            {CURRENCIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </Select>
          <Input
            placeholder="Solicitado por"
            aria-label="Solicitado por"
            value={values.requested_by}
            onChange={set("requested_by")}
            className="sm:col-span-2"
          />
          <div className="sm:col-span-2">
            <Button type="submit" disabled={confirm.isPending}>
              Guardar y confirmar
            </Button>
          </div>
        </form>
      )}
      <ErrorText>{error}</ErrorText>
    </div>
  );
}

function VoiceNotes({ tripId, isStaff }) {
  const { showToast } = useToast();
  const files = useList(["trip-files", tripId], `/intake/files?trip_id=${tripId}`);
  const notes = files.filter((f) => f.kind === "audio" && f.status === "processed");

  if (!notes.length) return <EmptyState>Sin notas de voz.</EmptyState>;

  return (
    <ul className="divide-y divide-slate-100">
      {notes.map((note) => {
        const result = note.extraction ?? {};
        const extraction = result.extraction ?? {};
        const route = [extraction.origin?.spoken, extraction.destination?.spoken].filter(Boolean).join(" → ");
        const mentions = (extraction.vehicle_mentions ?? [])
          .map((m) => [m.make, m.model, m.color].filter(Boolean).join(" "))
          .filter(Boolean);
        return (
          <li key={note.id} className="space-y-1 py-3 first:pt-0">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-slate-400">{new Date(note.created_at).toLocaleString()}</span>
              <button
                type="button"
                onClick={() => openIntakeFile(note.id).catch(() => showToast("No se pudo abrir el audio", "error"))}
                className="text-xs text-slate-600 hover:text-slate-900 hover:underline"
              >
                Escuchar
              </button>
            </div>
            {note.transcript && <p className="text-sm italic text-slate-700">«{note.transcript}»</p>}
            <p className="text-xs text-slate-500">
              {[
                route && `Dijo: ${route}`,
                isStaff && result.cost_amount != null && formatMoney(result.cost_amount, result.cost_currency),
                mentions.length && `Vehículos: ${mentions.join(", ")}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </li>
        );
      })}
    </ul>
  );
}

export default function TripPage() {
  const { tripId } = useParams();
  const { profile } = useAuth();
  const isStaff = profile?.role === "admin" || profile?.role === "dispatcher";

  const { data: trip, isLoading, error } = useQuery({
    queryKey: ["trip", tripId],
    queryFn: async () => (await apiClient.get(`/trips/${tripId}`)).data,
    retry: false,
  });
  const zones = useList(["zones"], "/zones");
  const trucks = useList(["trucks"], "/trucks");
  const drivers = useList(["drivers"], "/drivers", isStaff);

  const backTo = isStaff ? "/admin" : "/driver";
  const zoneName = (id) => zones.find((z) => z.id === id)?.name ?? "?";

  if (isLoading) {
    return (
      <Layout>
        <p className="text-sm text-slate-400">Cargando...</p>
      </Layout>
    );
  }
  if (error || !trip) {
    const status = error?.response?.status;
    return (
      <Layout>
        <Card>
          <EmptyState>{status === 403 ? "No tienes acceso a este viaje." : "No se encontró el viaje."}</EmptyState>
          <Link to={backTo} className="text-sm text-slate-600 hover:text-slate-900 hover:underline">
            ← Volver
          </Link>
        </Card>
      </Layout>
    );
  }

  const truck = trucks.find((t) => t.id === trip.truck_id);
  const driver = drivers.find((d) => d.id === trip.driver_id);

  return (
    <Layout>
      <div className="space-y-6">
        <Link to={backTo} className="text-sm text-slate-500 hover:text-slate-900">
          ← Volver
        </Link>

        <Card title="Viaje" action={<ReviewBadge status={trip.review_status} />}>
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-medium text-slate-900">
                {[driver?.full_name, truck?.plate].filter(Boolean).join(" · ") || "Viaje"}
              </span>
              <Badge tone={trip.status === "completed" ? "emerald" : "amber"}>
                {trip.status === "completed" ? "Completado" : "En curso"}
              </Badge>
            </div>
            <p className="text-sm text-slate-600">
              {zoneName(trip.origin_zone_id)} → {zoneName(trip.destination_zone_id)}
            </p>
            {(trip.origin_text || trip.destination_text) && (
              <p className="text-xs text-slate-400">
                Según la nota de voz: {[trip.origin_text, trip.destination_text].filter(Boolean).join(" → ")}
              </p>
            )}
            <p className="text-xs text-slate-400">
              Salió {new Date(trip.started_at).toLocaleString()}
              {trip.completed_at && ` · Llegó ${new Date(trip.completed_at).toLocaleString()}`}
              {` · ${SOURCE_LABEL[trip.intake_source] ?? ""}`}
            </p>
            {trip.requested_by && <p className="text-sm text-slate-600">Solicitado por {trip.requested_by}</p>}
            {isStaff && (
              <p className="text-sm text-slate-900">
                {trip.amount != null ? formatMoney(trip.amount, trip.currency) : <span className="text-slate-400">Sin monto</span>}
                {trip.trip_type === "directo" && <span className="text-xs text-slate-400"> · directo, suma de los vehículos</span>}
              </p>
            )}
            {trip.review_status === "needs_review" && <ReviewNotes notes={trip.review_notes} className="pt-1" />}
          </div>
          {isStaff && (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <ReviewEditor trip={trip} zones={zones} />
            </div>
          )}
        </Card>

        <Card>
          <IntakeUpload tripId={trip.id} showAmounts={isStaff} />
          <TripCarsPanel
            tripId={trip.id}
            currency={trip.currency}
            canAdd={isStaff}
            canDelete={isStaff}
            canEdit={isStaff}
          />
        </Card>

        <Card title="Notas de voz">
          <VoiceNotes tripId={trip.id} isStaff={isStaff} />
        </Card>
      </div>
    </Layout>
  );
}
