from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, require_csrf
from app.models import Cuenta, MetaAhorro
from app.schemas.common import ok
from app.schemas.modulos import MetaAhorroUpsert
from app.services.movimientos import cuenta_propia

router = APIRouter(prefix="/ahorros", tags=["ahorros"], dependencies=[Depends(require_csrf)])

# Saldo histórico de las cuentas de ahorro (mismo criterio que el dashboard)
_SALDOS_AHORRO_SQL = text("""
    SELECT c.id, c.nombre,
           COALESCE(c.saldo_inicial, 0)
             + COALESCE((SELECT SUM(i.monto) FROM ingresos i
                         WHERE i.cuenta_id = c.id AND i.usuario_id = :uid), 0)
             - COALESCE((SELECT SUM(t.monto) FROM transacciones t
                         WHERE t.cuenta_id = c.id AND t.usuario_id = :uid), 0) AS saldo
    FROM cuentas c
    WHERE c.usuario_id = :uid AND c.activa AND c.tipo = 'ahorro'
    ORDER BY c.nombre
""")


@router.get("")
async def listar(
    user: UsuarioActual = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    saldos = (await db.execute(_SALDOS_AHORRO_SQL, {"uid": user.usuario_id})).all()
    metas = {
        m.cuenta_id: m
        for m in (
            await db.scalars(
                select(MetaAhorro).join(Cuenta, Cuenta.id == MetaAhorro.cuenta_id).where(
                    Cuenta.usuario_id == user.usuario_id
                )
            )
        ).all()
    }

    items = []
    for fila in saldos:
        meta = metas.get(fila.id)
        saldo = float(fila.saldo)
        objetivo = float(meta.monto_objetivo) if meta else None
        items.append(
            {
                "cuenta_id": fila.id,
                "nombre": fila.nombre,
                "saldo": saldo,
                "meta": (
                    {
                        "monto_objetivo": objetivo,
                        "fecha_objetivo": meta.fecha_objetivo,
                        "porcentaje": round(saldo / objetivo * 100, 1) if objetivo else 0.0,
                        "falta": max(objetivo - saldo, 0) if objetivo else None,
                        "cumplida": objetivo is not None and saldo >= objetivo,
                    }
                    if meta
                    else None
                ),
            }
        )

    return ok({"items": items, "total_ahorrado": sum(i["saldo"] for i in items)})


@router.put("/{cuenta_id}/meta")
async def definir_meta(
    cuenta_id: int,
    body: MetaAhorroUpsert,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea o actualiza la meta de una cuenta (la convierte a tipo 'ahorro')."""
    cuenta = await cuenta_propia(db, user.usuario_id, cuenta_id)
    cuenta.tipo = "ahorro"

    meta = await db.scalar(select(MetaAhorro).where(MetaAhorro.cuenta_id == cuenta_id))
    if meta is None:
        meta = MetaAhorro(cuenta_id=cuenta_id, **body.model_dump())
        db.add(meta)
    else:
        for campo, valor in body.model_dump().items():
            setattr(meta, campo, valor)
    await db.flush()

    return ok(
        {
            "cuenta_id": cuenta_id,
            "monto_objetivo": float(meta.monto_objetivo),
            "fecha_objetivo": meta.fecha_objetivo,
        }
    )


@router.delete("/{cuenta_id}/meta")
async def quitar_meta(
    cuenta_id: int,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await cuenta_propia(db, user.usuario_id, cuenta_id)
    meta = await db.scalar(select(MetaAhorro).where(MetaAhorro.cuenta_id == cuenta_id))
    if meta is not None:
        await db.delete(meta)
    return ok({"eliminada": meta is not None})
