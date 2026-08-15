"""JWT de Supabase, cookies HttpOnly y utilidades de hashing.

Decisiones (plan 2026-08-14):
- FastAPI actúa de proxy de GoTrue: el frontend nunca ve el token.
- Cookies: sb_access (Path=/api, 15 min) y sb_refresh (Path=/api/v1/auth/refresh, 7 días),
  HttpOnly + Secure + SameSite=Strict.
- CSRF: SameSite=Strict + header X-Requested-With obligatorio en mutaciones.
"""
import hashlib
import time

import jwt
from fastapi import HTTPException, Response

from app.core.config import get_settings

COOKIE_ACCESS = "sb_access"
COOKIE_REFRESH = "sb_refresh"
ACCESS_MAX_AGE = 900  # 15 min
REFRESH_MAX_AGE = 604_800  # 7 días

_JWT_LEEWAY = 30  # segundos de tolerancia de reloj


def decode_supabase_jwt(token: str) -> dict:
    """Valida firma, expiración y audiencia del JWT de Supabase. Devuelve los claims."""
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="token_invalido")

    alg = header.get("alg", "HS256")
    try:
        if alg == "HS256":
            # Proyectos Supabase con legacy JWT secret
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                leeway=_JWT_LEEWAY,
            )
        # Proyectos con signing keys asimétricas (ES256/RS256): validar contra JWKS
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            leeway=_JWT_LEEWAY,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="token_invalido")


_jwks_client_cache: dict = {}


def _get_jwks_client() -> "jwt.PyJWKClient":
    """PyJWKClient cacheado en proceso (el propio cliente cachea las keys 24h)."""
    settings = get_settings()
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    cached = _jwks_client_cache.get(url)
    if cached is None:
        cached = jwt.PyJWKClient(url, cache_keys=True, lifespan=86_400)
        _jwks_client_cache[url] = cached
    return cached


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = get_settings().cookie_secure
    response.set_cookie(
        COOKIE_ACCESS, access_token,
        max_age=ACCESS_MAX_AGE, httponly=True, secure=secure, samesite="strict", path="/api",
    )
    response.set_cookie(
        COOKIE_REFRESH, refresh_token,
        max_age=REFRESH_MAX_AGE, httponly=True, secure=secure,
        samesite="strict", path="/api/v1/auth/refresh",
    )


def clear_auth_cookies(response: Response) -> None:
    secure = get_settings().cookie_secure
    response.set_cookie(
        COOKIE_ACCESS, "", max_age=0, httponly=True, secure=secure, samesite="strict", path="/api",
    )
    response.set_cookie(
        COOKIE_REFRESH, "", max_age=0, httponly=True, secure=secure,
        samesite="strict", path="/api/v1/auth/refresh",
    )


def hash_codigo(codigo: str) -> str:
    """SHA-256 hex del código de vinculación (normalizado a mayúsculas sin espacios)."""
    return hashlib.sha256(codigo.strip().upper().encode()).hexdigest()


# --- Cache en proceso auth_uid -> usuario_id (evita un SELECT por request) ---

_VINCULO_TTL = 300  # 5 min
_vinculo_cache: dict[str, tuple[int, float]] = {}


def vinculo_cache_get(auth_uid: str) -> int | None:
    entrada = _vinculo_cache.get(auth_uid)
    if entrada is None:
        return None
    usuario_id, expira = entrada
    if time.monotonic() > expira:
        _vinculo_cache.pop(auth_uid, None)
        return None
    return usuario_id


def vinculo_cache_set(auth_uid: str, usuario_id: int) -> None:
    _vinculo_cache[auth_uid] = (usuario_id, time.monotonic() + _VINCULO_TTL)


def vinculo_cache_clear() -> None:
    _vinculo_cache.clear()
