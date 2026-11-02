import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";

import { useToast } from "../context/ToastContext";
import { formatMoney } from "../lib/formatMoney";
import {
  MAX_AUDIO_BYTES,
  MAX_PHOTO_BYTES,
  MAX_PHOTOS_PER_VEHICLE,
  intakeErrorMessage,
  invalidateIntake,
  uploadVehiclePhotos,
  uploadVoiceNote,
} from "../lib/intake";
import { Button, ErrorText, ReviewBadge, ReviewNotes } from "./ui";

const fileButton =
  "inline-flex cursor-pointer items-center justify-center rounded-lg px-3 py-2.5 text-sm font-medium transition sm:py-1.5";
const primaryButton = `${fileButton} bg-slate-900 text-white hover:bg-slate-800`;
const ghostButton = `${fileButton} border border-slate-300 text-slate-700 hover:bg-slate-100`;

function FilePicker({ label, accept, capture, multiple, className, onPick, disabled }) {
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
        multiple={multiple}
        className="sr-only"
        disabled={disabled}
        onChange={(e) => {
          const files = [...(e.target.files ?? [])];
          e.target.value = "";
          if (files.length) onPick(files);
        }}
      />
    </>
  );
}

function PhotoTray({ files, onRemove }) {
  const [urls, setUrls] = useState([]);

  useEffect(() => {
    const created = files.map((file) => URL.createObjectURL(file));
    setUrls(created);
    return () => created.forEach((url) => URL.revokeObjectURL(url));
  }, [files]);

  return (
    <ul className="flex flex-wrap gap-2">
      {urls.map((url, index) => (
        <li key={url} className="relative">
          <img
            src={url}
            alt={`Foto ${index + 1} del vehículo`}
            className="h-16 w-16 rounded-md border border-slate-200 object-cover"
          />
          <button
            type="button"
            onClick={() => onRemove(index)}
            aria-label={`Quitar foto ${index + 1}`}
            className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-white text-xs text-slate-600 shadow-sm ring-1 ring-slate-300 hover:text-slate-900"
          >
            ×
          </button>
        </li>
      ))}
    </ul>
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
  const vehicle = [result.make ?? decoded?.make ?? result.wmi_make, result.model ?? decoded?.model, result.model_year]
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
        {result.duplicate ? " · Estas fotos ya se habían subido" : ""}
      </p>
      <ReviewNotes notes={result.review_reasons} />
    </div>
  );
}

function AudioResult({ result, showAmounts }) {
  const extraction = result.extraction;
  const route = [extraction?.origin?.normalized, extraction?.destination?.normalized].filter(Boolean).join(" → ");
  const reasons = result.trip_id ? result.trip_review_reasons : result.review_reasons;
  const status = result.trip_id ? result.trip_review_status : result.review_status;
  const details = [
    extraction?.unit_code && `Unidad ${extraction.unit_code}`,
    result.requested_by && `Solicita ${result.requested_by}`,
    extraction?.invoice_type === "directa" && "Factura directa",
  ].filter(Boolean);

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-900">{route || "Sin origen ni destino"}</span>
        <ReviewBadge status={status} />
      </div>
      {details.length > 0 && <p className="text-xs text-slate-500">{details.join(" · ")}</p>}
      {showAmounts && result.cost_amount != null && (
        <p className="text-sm text-slate-700">
          {formatMoney(result.cost_amount, result.cost_currency)}
          {result.cost_per_vehicle ? " por vehículo" : ""}
          {extraction?.cost_spoken ? <span className="text-slate-400"> · «{extraction.cost_spoken}»</span> : null}
        </p>
      )}
      {result.transcript && <p className="text-xs italic text-slate-500">«{result.transcript}»</p>}
      {result.duplicate && <p className="text-xs text-slate-400">Esta nota ya se había subido</p>}
      <ReviewNotes notes={reasons} />
    </div>
  );
}

export function IntakeUpload({ tripId, title = "Captura automática", showAmounts = true }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [tray, setTray] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const photos = useMutation({
    mutationFn: (files) => uploadVehiclePhotos(files, tripId),
    onSuccess: (data) => {
      setTray([]);
      setResult({ kind: "photo", data });
      invalidateIntake(queryClient, tripId);
      showToast(data.review_status === "needs_review" ? "Vehículo leído: hay algo por revisar" : "Vehículo leído");
    },
    onError: (err) => setError(intakeErrorMessage(err, "No se pudieron leer las fotos. Intenta de nuevo.")),
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

  const busy = photos.isPending || audio.isPending;
  const trayFull = tray.length >= MAX_PHOTOS_PER_VEHICLE;

  function addPhotos(files) {
    setError("");
    setResult(null);
    if (files.some((file) => file.size > MAX_PHOTO_BYTES)) {
      setError("Alguna foto pesa más de 10 MB.");
      return;
    }
    if (tray.length + files.length > MAX_PHOTOS_PER_VEHICLE) {
      setError(`Máximo ${MAX_PHOTOS_PER_VEHICLE} fotos por vehículo.`);
    }
    setTray((current) => [...current, ...files].slice(0, MAX_PHOTOS_PER_VEHICLE));
  }

  function pickAudio([file]) {
    setError("");
    setResult(null);
    if (file.size > MAX_AUDIO_BYTES) {
      setError("La nota de voz pesa más de 25 MB.");
      return;
    }
    audio.mutate(file);
  }

  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</p>
        <p className="mt-1 text-xs text-slate-400">
          Por vehículo: la foto de la etiqueta del VIN y, si se puede, una del carro donde se lea el modelo.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap">
        <FilePicker
          label={tray.length ? "Tomar otra foto" : "Tomar foto del VIN"}
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          className={tray.length ? ghostButton : primaryButton}
          disabled={busy || trayFull}
          onPick={addPhotos}
        />
        <FilePicker
          label="Elegir fotos"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className={ghostButton}
          disabled={busy || trayFull}
          onPick={addPhotos}
        />
        <FilePicker
          label="Subir nota de voz"
          accept="audio/*,.ogg,.opus,.m4a,.mp3,.wav,.webm"
          className={ghostButton}
          disabled={busy}
          onPick={pickAudio}
        />
      </div>

      {tray.length > 0 && (
        <div className="space-y-2 rounded-lg border border-slate-200 p-3">
          <PhotoTray files={tray} onRemove={(index) => setTray((current) => current.filter((_, i) => i !== index))} />
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => photos.mutate(tray)} disabled={busy} className="w-full sm:w-auto">
              {photos.isPending ? "Leyendo…" : `Leer vehículo (${tray.length} ${tray.length === 1 ? "foto" : "fotos"})`}
            </Button>
            <Button variant="ghost" onClick={() => setTray([])} disabled={busy}>
              Descartar fotos
            </Button>
          </div>
        </div>
      )}

      {busy && (
        <p className="text-sm text-slate-500" role="status" aria-live="polite">
          {photos.isPending ? "Leyendo el VIN y el vehículo…" : "Transcribiendo la nota de voz…"}
        </p>
      )}
      <ErrorText>{error}</ErrorText>
      {result && (
        <div className="rounded-lg border border-slate-200 p-3" role="status" aria-live="polite">
          {result.kind === "photo" ? (
            <PhotoResult result={result.data} />
          ) : (
            <AudioResult result={result.data} showAmounts={showAmounts} />
          )}
        </div>
      )}
    </div>
  );
}
