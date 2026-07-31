import { useState } from "react";

import { apiClient } from "../../lib/apiClient";
import { Button, Card, ErrorText } from "../../components/ui";
import { useToast } from "../../context/ToastContext";

export default function FeSection() {
  const { showToast } = useToast();
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  async function handleDownload() {
    setError("");
    setDownloading(true);
    try {
      const response = await apiClient.get("/trips/export/fe", { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "FE.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showToast("Descarga iniciada");
    } catch {
      setError("No se pudo generar el archivo. Intentá de nuevo.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card title="FE">
      <p className="text-sm text-slate-500">
        Descargá un resumen en Excel de todos los viajes: código de camión, placa, destino
        inicial y final, monto, marca del carro y un enlace a la foto del VIN subida por cada
        carro transportado.
      </p>
      <Button className="mt-4" onClick={handleDownload} disabled={downloading}>
        {downloading ? "Generando..." : "Descargar Excel"}
      </Button>
      <div className="mt-2">
        <ErrorText>{error}</ErrorText>
      </div>
    </Card>
  );
}
