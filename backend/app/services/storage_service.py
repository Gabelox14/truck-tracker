import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SIGNED_URL_SECONDS = 600

_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/wav": "wav",
    "audio/webm": "webm",
}


class StorageError(RuntimeError):
    pass


def object_path(folder: str, sha256: str, media_type: str) -> str:
    """Ruta por contenido: el mismo archivo siempre cae en la misma ruta."""
    return f"{folder}/{sha256[:2]}/{sha256}.{_EXTENSIONS.get(media_type, 'bin')}"


class SupabaseStorage:
    """Bucket privado de Supabase Storage, usado solo con la llave de servicio."""

    def __init__(self, base_url: str, service_key: str, bucket: str, http_client: httpx.Client | None = None):
        self._base = f"{base_url.rstrip('/')}/storage/v1"
        self._headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        self.bucket = bucket
        self._client = http_client or httpx.Client(timeout=30.0)

    def _check(self, response: httpx.Response, action: str) -> httpx.Response:
        if response.status_code >= 400:
            logger.error("storage %s failed status=%s body=%s", action, response.status_code, response.text[:300])
            raise StorageError(f"No se pudo {action} el archivo en Storage")
        return response

    def upload(self, path: str, data: bytes, content_type: str) -> None:
        try:
            response = self._client.post(
                f"{self._base}/object/{self.bucket}/{path}",
                content=data,
                headers={**self._headers, "Content-Type": content_type, "x-upsert": "true"},
            )
        except httpx.HTTPError as exc:
            raise StorageError("No se pudo guardar el archivo en Storage") from exc
        self._check(response, "guardar")

    def download(self, path: str) -> bytes:
        try:
            response = self._client.get(f"{self._base}/object/{self.bucket}/{path}", headers=self._headers)
        except httpx.HTTPError as exc:
            raise StorageError("No se pudo leer el archivo en Storage") from exc
        return self._check(response, "leer").content

    def signed_url(self, path: str, expires_in: int = SIGNED_URL_SECONDS) -> str:
        try:
            response = self._client.post(
                f"{self._base}/object/sign/{self.bucket}/{path}",
                json={"expiresIn": expires_in},
                headers=self._headers,
            )
        except httpx.HTTPError as exc:
            raise StorageError("No se pudo generar el enlace del archivo") from exc
        signed = self._check(response, "firmar").json()["signedURL"]
        return f"{self._base}{signed}"

    def delete(self, path: str) -> None:
        try:
            response = self._client.request(
                "DELETE", f"{self._base}/object/{self.bucket}", json={"prefixes": [path]}, headers=self._headers
            )
        except httpx.HTTPError as exc:
            raise StorageError("No se pudo borrar el archivo en Storage") from exc
        self._check(response, "borrar")


_storage: SupabaseStorage | None = None


def get_storage() -> SupabaseStorage:
    global _storage
    if _storage is None:
        _storage = SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key, settings.intake_bucket)
    return _storage
