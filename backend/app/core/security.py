import time

import httpx
from jose import jwt

from app.core.config import settings

_JWKS_TTL_SECONDS = 3600
_jwks_cache: dict[str, object] = {"keys": [], "fetched_at": 0.0}


def _get_jwks() -> list[dict]:
    now = time.time()
    if not _jwks_cache["keys"] or now - _jwks_cache["fetched_at"] > _JWKS_TTL_SECONDS:
        url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        _jwks_cache["keys"] = response.json()["keys"]
        _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]


def verify_supabase_token(token: str) -> dict:
    """Verify a Supabase-issued access token against the project's JWKS
    (asymmetric ES256 signing keys) and return its decoded claims."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    key = next((k for k in _get_jwks() if k["kid"] == kid), None)
    if key is None:
        raise jwt.JWTError("Signing key not found")
    return jwt.decode(token, key, algorithms=[key["alg"]], audience="authenticated")
