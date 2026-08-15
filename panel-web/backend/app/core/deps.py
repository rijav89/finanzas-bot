"""Dependencias FastAPI: usuario actual, sesión de BD con RLS y guard CSRF."""
import uuid
from dataclasses import dataclass
from typing import AsyncIterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    COOKIE_ACCESS,
    decode_supabase_jwt,
    vinculo_cache_get,
    vinculo_cache_set,
)
from app.db.session import async_session
from app.models import VinculoAuth


@dataclass
class UsuarioActual:
    auth_uid: str
    usuario_id: int
    email: str | None = None


async def get_current_user(request: Request) -> UsuarioActual:
    """Lee la cookie sb_access, valida el JWT y resuelve usuario_id vía vinculos_auth.

    401 sin token/token inválido; 409 vinculo_requerido si el usuario web
    aún no vinculó su cuenta de Telegram.
    """
    token = request.cookies.get(COOKIE_ACCESS)
    if not token:
        raise HTTPException(status_code=401, detail="no_autenticado")
    claims = decode_supabase_jwt(token)
    auth_uid = claims.get("sub")
    if not auth_uid:
        raise HTTPException(status_code=401, detail="token_invalido")

    usuario_id = vinculo_cache_get(auth_uid)
    if usuario_id is None:
        try:
            auth_uuid = uuid.UUID(auth_uid)
        except ValueError:
            raise HTTPException(status_code=401, detail="token_invalido")
        async with async_session() as session:
            fila = await session.scalar(
                select(VinculoAuth.usuario_id).where(VinculoAuth.auth_uid == auth_uuid)
            )
        if fila is None:
            raise HTTPException(status_code=409, detail="vinculo_requerido")
        usuario_id = fila
        vinculo_cache_set(auth_uid, usuario_id)

    return UsuarioActual(auth_uid=auth_uid, usuario_id=usuario_id, email=claims.get("email"))


async def get_db(
    user: UsuarioActual = Depends(get_current_user),
) -> AsyncIterator[AsyncSession]:
    """Sesión con transacción abierta y GUC app.usuario_id seteado (SET LOCAL).

    El GUC alimenta las políticas RLS (migración 004, F6). set_config(..., true)
    es local a la transacción → compatible con el pooler de Supabase.
    El commit es automático al salir sin excepción.
    """
    async with async_session() as session:
        async with session.begin():
            if session.bind.dialect.name == "postgresql":
                await session.execute(
                    text("SELECT set_config('app.usuario_id', :uid, true)"),
                    {"uid": str(user.usuario_id)},
                )
            yield session


async def get_auth_claims(request: Request) -> dict:
    """Solo valida el JWT (sin exigir vínculo). Para /auth/vincular y /auth/me."""
    token = request.cookies.get(COOKIE_ACCESS)
    if not token:
        raise HTTPException(status_code=401, detail="no_autenticado")
    claims = decode_supabase_jwt(token)
    if not claims.get("sub"):
        raise HTTPException(status_code=401, detail="token_invalido")
    return claims


async def get_db_basico() -> AsyncIterator[AsyncSession]:
    """Sesión transaccional SIN GUC de usuario — solo para el flujo de vinculación,
    donde aún no existe usuario_id. Las políticas RLS de la migración 004 deben
    contemplar este camino para vinculos_auth/codigos_vinculacion."""
    async with async_session() as session:
        async with session.begin():
            yield session


async def require_csrf(request: Request) -> None:
    """Defensa CSRF: exigir header custom en toda mutación (fuerza same-origin).

    Se suma a SameSite=Strict de las cookies. El frontend siempre envía
    X-Requested-With: fetch en su wrapper.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if request.headers.get("x-requested-with") != "fetch":
            raise HTTPException(status_code=403, detail="csrf_header_requerido")
