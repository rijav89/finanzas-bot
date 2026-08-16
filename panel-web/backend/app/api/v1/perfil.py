from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, require_csrf
from app.models import Meta, PerfilFinanciero
from app.schemas.common import ok
from app.schemas.modulos import MetaCrear, MetaEditar, PerfilUpsert
from app.services.movimientos import cuenta_propia

router = APIRouter(tags=["perfil"], dependencies=[Depends(require_csrf)])


def _serializar_perfil(p: PerfilFinanciero | None) -> dict | None:
    if p is None:
        return None
    return {
        "ingreso_mensual_declarado": (
            float(p.ingreso_mensual_declarado)
            if p.ingreso_mensual_declarado is not None
            else None
        ),
        "moneda": p.moneda,
        "perfil_riesgo": p.perfil_riesgo,
        "contexto_ia": p.contexto_ia,
        "actualizado_en": p.actualizado_en,
    }


@router.get("/perfil")
async def ver_perfil(
    user: UsuarioActual = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    perfil = await db.scalar(
        select(PerfilFinanciero).where(PerfilFinanciero.usuario_id == user.usuario_id)
    )
    return ok(_serializar_perfil(perfil))


@router.put("/perfil")
async def guardar_perfil(
    body: PerfilUpsert,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    perfil = await db.scalar(
        select(PerfilFinanciero).where(PerfilFinanciero.usuario_id == user.usuario_id)
    )
    if perfil is None:
        perfil = PerfilFinanciero(usuario_id=user.usuario_id, **body.model_dump())
        db.add(perfil)
    else:
        for campo, valor in body.model_dump().items():
            setattr(perfil, campo, valor)
        perfil.actualizado_en = func.now()
    await db.flush()
    await db.refresh(perfil)
    return ok(_serializar_perfil(perfil))


def _serializar_meta(m: Meta) -> dict:
    return {
        "id": m.id,
        "titulo": m.titulo,
        "tipo": m.tipo,
        "monto_objetivo": float(m.monto_objetivo) if m.monto_objetivo is not None else None,
        "fecha_objetivo": m.fecha_objetivo,
        "cuenta_id": m.cuenta_id,
        "cumplida": m.cumplida,
    }


@router.get("/metas")
async def listar_metas(
    user: UsuarioActual = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    filas = (
        await db.scalars(
            select(Meta)
            .where(Meta.usuario_id == user.usuario_id)
            .order_by(Meta.cumplida, Meta.fecha_objetivo.nulls_last())
        )
    ).all()
    return ok([_serializar_meta(m) for m in filas])


@router.post("/metas", status_code=201)
async def crear_meta(
    body: MetaCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.cuenta_id is not None:
        await cuenta_propia(db, user.usuario_id, body.cuenta_id)
    meta = Meta(usuario_id=user.usuario_id, **body.model_dump())
    db.add(meta)
    await db.flush()
    return ok(_serializar_meta(meta))


@router.patch("/metas/{meta_id}")
async def editar_meta(
    meta_id: int,
    body: MetaEditar,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    meta = await _meta_propia(db, user.usuario_id, meta_id)
    cambios = body.model_dump(exclude_unset=True)
    if cambios.get("cuenta_id") is not None:
        await cuenta_propia(db, user.usuario_id, cambios["cuenta_id"])
    for campo, valor in cambios.items():
        setattr(meta, campo, valor)
    await db.flush()
    return ok(_serializar_meta(meta))


@router.delete("/metas/{meta_id}")
async def eliminar_meta(
    meta_id: int,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    meta = await _meta_propia(db, user.usuario_id, meta_id)
    await db.delete(meta)
    return ok({"eliminada": True})


async def _meta_propia(db: AsyncSession, usuario_id: int, meta_id: int) -> Meta:
    meta = await db.scalar(
        select(Meta).where(Meta.id == meta_id, Meta.usuario_id == usuario_id)
    )
    if meta is None:
        raise HTTPException(status_code=404, detail="meta_no_encontrada")
    return meta
