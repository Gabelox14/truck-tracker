import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../lib/apiClient";
import { uploadVinPhoto } from "../lib/uploadVinPhoto";
import { useToast } from "../context/ToastContext";
import { Button, ErrorText, Input } from "./ui";

function RemoveCarButton({ onConfirm, pending }) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <span className="inline-flex items-center gap-2 text-xs">
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

export function TripCarsPanel({ tripId, canAdd = false, canDelete = false }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [brand, setBrand] = useState("");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const { data: cars } = useQuery({
    queryKey: ["trip-cars", tripId],
    queryFn: async () => (await apiClient.get(`/trips/${tripId}/cars`)).data,
  });

  const addCar = useMutation({
    mutationFn: async (payload) => (await apiClient.post(`/trips/${tripId}/cars`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trip-cars", tripId] });
      setBrand("");
      setFile(null);
      setError("");
      showToast("Carro agregado");
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo agregar el carro"),
  });

  const removeCar = useMutation({
    mutationFn: async (carId) => apiClient.delete(`/trips/${tripId}/cars/${carId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trip-cars", tripId] });
      showToast("Carro quitado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo quitar el carro", "error"),
  });

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      let vinPhotoUrl = null;
      if (file) {
        setUploading(true);
        vinPhotoUrl = await uploadVinPhoto(file);
      }
      addCar.mutate({ brand, vin_photo_url: vinPhotoUrl });
    } catch (err) {
      setError(err.message ?? "No se pudo subir la foto");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mt-4 border-t border-slate-100 pt-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Carros transportados
      </p>

      {cars?.length ? (
        <ul className="space-y-2">
          {cars.map((car) => (
            <li key={car.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <div className="flex min-w-0 items-center gap-2">
                {car.vin_photo_url && (
                  <a href={car.vin_photo_url} target="_blank" rel="noreferrer">
                    <img
                      src={car.vin_photo_url}
                      alt={`VIN de ${car.brand}`}
                      className="h-10 w-10 shrink-0 rounded-md border border-slate-200 object-cover"
                    />
                  </a>
                )}
                <span className="truncate text-slate-900">{car.brand}</span>
              </div>
              {canDelete && (
                <RemoveCarButton pending={removeCar.isPending} onConfirm={() => removeCar.mutate(car.id)} />
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-400">Sin carros agregados.</p>
      )}

      {canAdd && (
        <form onSubmit={handleSubmit} className="mt-3 flex flex-col gap-2 sm:flex-row">
          <Input
            placeholder="Marca del carro"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            required
          />
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm text-slate-600 file:mr-2 file:rounded-md file:border-0 file:bg-slate-100 file:px-2 file:py-1.5 file:text-sm sm:w-auto"
          />
          <Button type="submit" disabled={uploading || addCar.isPending}>
            {uploading ? "Subiendo..." : "Agregar"}
          </Button>
        </form>
      )}
      <ErrorText>{error}</ErrorText>
    </div>
  );
}
