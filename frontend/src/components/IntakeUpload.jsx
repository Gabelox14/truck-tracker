import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { useToast } from "../context/ToastContext";
import { formatMoney } from "../lib/formatMoney";
import {
  MAX_AUDIO_BYTES,
  MAX_PHOTO_BYTES,
  intakeErrorMessage,
  invalidateIntake,
  uploadVinPhoto,
  uploadVoiceNote,
} from "../lib/intake";
import { ErrorText, ReviewBadge, ReviewNotes } from "./ui";

const fileButton =
  "inline-flex cursor-pointer items-center justify-center rounded-lg px-3 py-2.5 text-sm font-medium transition sm:py-1.5";
const primaryButton = `${fileButton} bg-slate-900 text-white hover:bg-slate-800`;
const ghostButton = `${fileButton} border border-slate-300 text-slate-700 hover:bg-slate-100`;

function FilePicker({ label, accept, capture, className, onPick, disabled }) {
  const id = useId();
  return (
    <>
      <label htmlFor={id} className={`${className} ${disabled ? "pointer-events-none opacity-50" : ""}`}>
        {label}
      </label>
      <input
        id={id}
        type="file"
        accept={accept}
        capture={capture}
        className="sr-only"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (file) onPick(file);
        }}
      />
    </>
  );
}

function PhotoResult({ result }) {
  const vinHint = !result.vin
    ? "No se leyó un VIN"
    : !result.vin_valid
      ? "No es un VIN de 17 caracteres"
      : result.check_digit_ok
        ? "VIN válido"
        : "El dígito verificador no cuadra";
  const decoded = result.nhtsa;
  const vehicle = [result.make ?? decoded?.make, decoded?.model ?? result.model, decoded?.model_year]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-900">{vehicle || "Vehículo sin identificar"}</span>
        <ReviewBadge status={result.review_status} />
      </div>
      {result.vin && <p className="font-mono text-sm text-slate-700">{result.vin}</p>}
      <p className="text-xs text-slate-400">
        {vinHint}
        {result.duplicate ? " · Esta foto ya se había subido" : ""}
      </p>
      <ReviewNotes notes={result.review_reasons} />
    </div>
  );
}

function AudioResult({ result }) {
  const extraction = result.extraction;
  const route = [extraction?.origin?.normalized, extraction?.destination?.normalized].filter(Boolean).join(" → ");
  const reasons = result.trip_id ? result.trip_review_reasons : result.review_reasons;
  const status = result.trip_id ? result.trip_review_status : result.review_status;

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-900">{route || "Sin origen ni destino"}</span>
        <ReviewBadge status={status} />
      </div>
      {result.cost_amount != null && (
        <p className="text-sm text-slate-700">
          {formatMoney(result.cost_amount, result.cost_currency)}
          {extraction?.cost_spoken ? <span className="text-slate-400"> · «{extraction.cost_spoken}»</span> : null}
        </p>
      )}
      {result.transcript && <p className="text-xs italic text-slate-500">«{result.transcript}»</p>}
      {result.duplicate && <p className="text-xs text-slate-400">Esta nota ya se había subido</p>}
      <ReviewNotes notes={reasons} />
    </div>
  );
}

export function IntakeUpload({ tripId, title = "Captura automática" }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const photo = useMutation({
    mutationFn: (file) => uploadVinPhoto(file, tripId),
    onSuccess: (data) => {
      setResult({ kind: "photo", data });
      invalidateIntake(queryClient, tripId);
      showToast(data.review_status === "needs_review" ? "Foto leída: hay algo por revisar" : "Foto leída");
    },
    onError: (err) => setError(intakeErrorMessage(err, "No se pudo leer la foto. Intenta de nuevo.")),
  });

  const audio = useMutation({
    mutationFn: (file) => uploadVoiceNote(file, tripId),
    onSuccess: (data) => {
      setResult({ kind: "audio", data });
      invalidateIntake(queryClient, tripId);
      showToast("Nota de voz procesada");
    },
    onError: (err) => setError(intakeErrorMessage(err, "No se pudo procesar la nota de voz. Intenta de nuevo.")),
  });

  const busy = photo.isPending || audio.isPending;

  function pick(file, maxBytes, mutation, tooBig) {
    setError("");
    setResult(null);
    if (file.size > maxBytes) {
      setError(tooBig);
      return;
    }
    mutation.mutate(file);
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</p>
      <div className="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap">
        <FilePicker
          label="Tomar foto del VIN"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          className={primaryButton}
          disabled={busy}
          onPick={(file) => pick(file, MAX_PHOTO_BYTES, photo, "La foto pesa más de 10 MB.")}
        />
        <FilePicker
          label="Elegir foto"
          accept="image/jpeg,image/png,image/webp"
          className={ghostButton}
          disabled={busy}
          onPick={(file) => pick(file, MAX_PHOTO_BYTES, photo, "La foto pesa más de 10 MB.")}
        />
        <FilePicker
          label="Subir nota de voz"
          accept="audio/*,.ogg,.opus,.m4a,.mp3,.wav,.webm"
          className={ghostButton}
          disabled={busy}
          onPick={(file) => pick(file, MAX_AUDIO_BYTES, audio, "La nota de voz pesa más de 25 MB.")}
        />
      </div>

      {busy && (
        <p className="text-sm text-slate-500" role="status" aria-live="polite">
          {photo.isPending ? "Leyendo el VIN de la foto…" : "Transcribiendo la nota de voz…"}
        </p>
      )}
      <ErrorText>{error}</ErrorText>
      {result && (
        <div className="rounded-lg border border-slate-200 p-3" role="status" aria-live="polite">
          {result.kind === "photo" ? <PhotoResult result={result.data} /> : <AudioResult result={result.data} />}
        </div>
      )}
    </div>
  );
}
