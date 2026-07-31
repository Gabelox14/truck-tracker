import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../lib/apiClient";
import { uploadVinPhoto } from "../lib/uploadVinPhoto";
import { Button, ErrorText, Input } from "./ui";

export function TripCarsPanel({ tripId, canAdd = false, canDelete = false }) {
  const queryClient = useQueryClient();
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
    },
    onError: (err) => setError(err.response?.data?.detail ?? "No se pudo agregar el carro"),
  });

  const removeCar = useMutation({
    mutationFn: async (carId) => apiClient.delete(`/trips/${tripId}/cars/${carId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["trip-cars", tripId] }),
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
            <li key={car.id} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                {car.vin_photo_url && (
                  <a href={car.vin_photo_url} target="_blank" rel="noreferrer">
                    <img
                      src={car.vin_photo_url}
                      alt={`VIN de ${car.brand}`}
                      className="h-10 w-10 rounded-md border border-slate-200 object-cover"
                    />
                  </a>
                )}
                <span className="text-slate-900">{car.brand}</span>
              </div>
              {canDelete && (
                <button
                  type="button"
                  onClick={() => removeCar.mutate(car.id)}
                  className="text-xs text-red-600 hover:underline"
                >
                  Quitar
                </button>
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
            className="text-sm text-slate-600 file:mr-2 file:rounded-md file:border-0 file:bg-slate-100 file:px-2 file:py-1.5 file:text-sm"
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
