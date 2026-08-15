from datetime import datetime, time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, require_csrf
from app.models import Ingreso, Transaccion
from app.schemas.common import ok
from app.schemas.movimientos import (
    GastoCrear,
    IngresoCrear,
    MovimientoEditar,
    TransferenciaCrear,
)
from app.services.movimientos import crear_transferencia, cuenta_propia

router = APIRouter(tags=["movimientos"], dependencies=[Depends(require_csrf)])

_MODELOS = {"gasto": Transaccion, "ingreso": Ingreso}


@router.get("/movimientos")
async def listar(
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tipo: Literal["gasto", "ingreso"] | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    categoria: str | None = Query(default=None, max_length=40),
    cuenta_id: int | None = None,
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Listado unificado gastos+ingresos con filtros (alimenta historial y cmdk)."""

    def _rama(modelo, etiqueta: str):
        # Columnas homogéneas para el UNION; las que no existen en ingresos van como NULL
        medio = modelo.medio if hasattr(modelo, "medio") else literal(None)
        destinatario = modelo.destinatario if hasattr(modelo, "destinatario") else literal(None)
        stmt = select(
            modelo.id,
            literal(etiqueta).label("tipo"),
            modelo.monto,
            modelo.categoria,
            modelo.descripcion,
            medio.label("medio"),
            destinatario.label("destinatario"),
            modelo.fecha,
            modelo.cuenta_id,
        ).where(modelo.usuario_id == user.usuario_id)
        if desde is not None:
            stmt = stmt.where(modelo.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(modelo.fecha < hasta)
        if categoria is not None:
            stmt = stmt.where(modelo.categoria == categoria)
        if cuenta_id is not None:
            stmt = stmt.where(modelo.cuenta_id == cuenta_id)
        if q:
            patron = f"%{q}%"
            if hasattr(modelo, "destinatario"):
                stmt = stmt.where(
                    modelo.descripcion.ilike(patron) | modelo.destinatario.ilike(patron)
                )
            else:
                stmt = stmt.where(modelo.descripcion.ilike(patron))
        return stmt

    ramas = []
    if tipo in (None, "gasto"):
        ramas.append(_rama(Transaccion, "gasto"))
    if tipo in (None, "ingreso"):
        ramas.append(_rama(Ingreso, "ingreso"))

    union = union_all(*ramas).subquery()
    filas = (
        await db.execute(
            select(union)
            .order_by(union.c.fecha.desc(), union.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    return ok(
        {
            "items": [
                {
                    "id": f.id,
                    "tipo": f.tipo,
                    "monto": f.monto,
                    "categoria": f.categoria,
                    "descripcion": f.descripcion,
                    "medio": f.medio,
                    "destinatario": f.destinatario,
                    "fecha": f.fecha,
                    "cuenta_id": f.cuenta_id,
                }
                for f in filas
            ],
            "limit": limit,
            "offset": offset,
        }
    )


@router.post("/gastos", status_code=201)
async def crear_gasto(
    body: GastoCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await cuenta_propia(db, user.usuario_id, body.cuenta_id)
    gasto = Transaccion(
        usuario_id=user.usuario_id,
        monto=body.monto,
        categoria=body.categoria,
        descripcion=body.descripcion,
        medio=body.medio,
        cuenta_id=body.cuenta_id,
    )
    if body.fecha is not None:
        gasto.fecha = datetime.combine(body.fecha, time(12, 0))
    db.add(gasto)
    await db.flush()
    return ok({"id": gasto.id, "tipo": "gasto"})


@router.post("/ingresos", status_code=201)
async def crear_ingreso(
    body: IngresoCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await cuenta_propia(db, user.usuario_id, body.cuenta_id)
    ingreso = Ingreso(
        usuario_id=user.usuario_id,
        monto=body.monto,
        categoria=body.categoria,
        descripcion=body.descripcion,
        cuenta_id=body.cuenta_id,
    )
    if body.fecha is not None:
        ingreso.fecha = datetime.combine(body.fecha, time(12, 0))
    db.add(ingreso)
    await db.flush()
    return ok({"id": ingreso.id, "tipo": "ingreso"})


@router.patch("/{tipo}/{mov_id}")
async def editar(
    tipo: Literal["gastos", "ingresos"],
    mov_id: int,
    body: MovimientoEditar,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    modelo = Transaccion if tipo == "gastos" else Ingreso
    fila = await db.scalar(
        select(modelo).where(modelo.id == mov_id, modelo.usuario_id == user.usuario_id)
    )
    if fila is None:
        raise HTTPException(status_code=404, detail="movimiento_no_encontrado")
    cambios = body.model_dump(exclude_unset=True)
    if "cuenta_id" in cambios:
        await cuenta_propia(db, user.usuario_id, cambios["cuenta_id"])
    for campo, valor in cambios.items():
        setattr(fila, campo, valor)
    return ok({"editado": True})


@router.delete("/{tipo}/{mov_id}")
async def eliminar(
    tipo: Literal["gastos", "ingresos"],
    mov_id: int,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    modelo = Transaccion if tipo == "gastos" else Ingreso
    fila = await db.scalar(
        select(modelo).where(modelo.id == mov_id, modelo.usuario_id == user.usuario_id)
    )
    if fila is None:
        raise HTTPException(status_code=404, detail="movimiento_no_encontrado")
    await db.delete(fila)
    return ok({"eliminado": True})


@router.post("/transferencias", status_code=201)
async def transferir(
    body: TransferenciaCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resultado = await crear_transferencia(
        db, user.usuario_id, body.origen_id, body.destino_id, body.monto
    )
    return ok(resultado)
