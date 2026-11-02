import { apiClient } from "./apiClient";

export const MAX_PHOTO_BYTES = 10 * 1024 * 1024;
export const MAX_AUDIO_BYTES = 25 * 1024 * 1024;

export const MAX_PHOTOS_PER_VEHICLE = 4;

function upload(path, field, files, tripId) {
  const form = new FormData();
  for (const file of files) form.append(field, file);
  if (tripId) form.append("trip_id", tripId);
  return apiClient.post(path, form).then((response) => response.data);
}

// Fotos del mismo vehículo (etiqueta del VIN y el carro): una sola lectura.
export function uploadVehiclePhotos(files, tripId) {
  return upload("/intake/vin-photo", "files", files, tripId);
}

export function uploadVoiceNote(file, tripId) {
  return upload("/intake/audio", "file", [file], tripId);
}

export function intakeErrorMessage(err, fallback) {
  if (err.response?.status === 503) {
    return "La captura automática todavía no está configurada en el servidor.";
  }
  return err.response?.data?.detail ?? fallback;
}

// Abre la pestaña antes de pedir el enlace firmado: si se abre después de un
// await, el navegador la toma como ventana emergente y la bloquea.
export async function openIntakeFile(fileId) {
  const tab = window.open("", "_blank");
  try {
    const { data } = await apiClient.get(`/intake/files/${fileId}/url`);
    if (tab) tab.location.href = data.url;
    else window.location.href = data.url;
  } catch (err) {
    tab?.close();
    throw err;
  }
}

export function invalidateIntake(queryClient, tripId) {
  for (const key of [["trips"], ["my-trips"], ["review-queue"], ["dashboard-stats"]]) {
    queryClient.invalidateQueries({ queryKey: key });
  }
  if (tripId) {
    for (const key of [["trip", tripId], ["trip-cars", tripId], ["trip-files", tripId]]) {
      queryClient.invalidateQueries({ queryKey: key });
    }
  }
}
