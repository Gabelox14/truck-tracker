import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Supabase no tiene "bloqueo indefinido": ~100 años.
BAN_FOREVER = "876000h"


class AuthAdminError(RuntimeError):
    pass


class AuthUserExists(AuthAdminError):
    pass


class SupabaseAuthAdmin:
    """API de administración de Supabase Auth, usada solo con la llave de servicio."""

    def __init__(self, base_url: str, service_key: str, http_client: httpx.Client | None = None):
        self._base = f"{base_url.rstrip('/')}/auth/v1/admin/users"
        self._headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        self._client = http_client or httpx.Client(timeout=20.0)

    def _send(self, method: str, url: str, action: str, json: dict | None = None) -> httpx.Response:
        try:
            response = self._client.request(method, url, json=json, headers=self._headers)
        except httpx.HTTPError as exc:
            raise AuthAdminError(f"No se pudo {action} la cuenta en Supabase") from exc
        if response.status_code >= 400:
            body = response.text[:300]
            logger.error("auth admin %s failed status=%s body=%s", action, response.status_code, body)
            if response.status_code == 422 and ("email_exists" in body or "already been registered" in body):
                raise AuthUserExists("Ese usuario ya existe")
            raise AuthAdminError(f"Supabase no pudo {action} la cuenta (error {response.status_code})")
        return response

    def create_user(self, email: str, password: str, full_name: str) -> str:
        """Crea la cuenta ya confirmada (no se envía correo) y devuelve su id."""
        payload = {"email": email, "password": password, "email_confirm": True, "user_metadata": {"full_name": full_name}}
        return self._send("POST", self._base, "crear", payload).json()["id"]

    def update_user(self, user_id: str, *, password: str) -> None:
        self._send("PUT", f"{self._base}/{user_id}", "actualizar", {"password": password})

    def set_banned(self, user_id: str, *, banned: bool) -> None:
        """Bloqueada no puede iniciar sesión ni renovar su sesión."""
        self._send("PUT", f"{self._base}/{user_id}", "actualizar", {"ban_duration": BAN_FOREVER if banned else "none"})

    def delete_user(self, user_id: str) -> None:
        self._send("DELETE", f"{self._base}/{user_id}", "eliminar")


_auth_admin: SupabaseAuthAdmin | None = None


def get_auth_admin() -> SupabaseAuthAdmin:
    global _auth_admin
    if _auth_admin is None:
        _auth_admin = SupabaseAuthAdmin(settings.supabase_url, settings.supabase_service_role_key)
    return _auth_admin
