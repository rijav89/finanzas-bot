"""Canje del código de vinculación Telegram ↔ Supabase Auth."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_codigo
from app.models import CodigoVinculacion, VinculoAuth


async def canjear_codigo(session: AsyncSession, auth_uid: str, codigo: str) -> int:
    """Valida el código (vigente, no usado) y crea el vínculo. Devuelve usuario_id.

    Todo ocurre dentro de la transacción de la request (get_db).
    """
    ya = await session.scalar(
        select(VinculoAuth.usuario_id).where(VinculoAuth.auth_uid == uuid.UUID(auth_uid))
    )
    if ya is not None:
        raise HTTPException(status_code=409, detail="ya_vinculado")

    fila = await session.scalar(
        select(CodigoVinculacion)
        .where(
            CodigoVinculacion.codigo_hash == hash_codigo(codigo),
            CodigoVinculacion.usado.is_(False),
            CodigoVinculacion.expira_en > datetime.now(timezone.utc),
        )
        .with_for_update()
    )
    if fila is None:
        raise HTTPException(status_code=400, detail="codigo_invalido_o_expirado")

    usuario_ya_vinculado = await session.scalar(
        select(VinculoAuth.id).where(VinculoAuth.usuario_id == fila.usuario_id)
    )
    if usuario_ya_vinculado is not None:
        raise HTTPException(status_code=409, detail="telegram_ya_vinculado")

    fila.usado = True
    session.add(VinculoAuth(usuario_id=fila.usuario_id, auth_uid=uuid.UUID(auth_uid)))
    return fila.usuario_id
