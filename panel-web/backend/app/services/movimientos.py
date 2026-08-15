"""Reglas de negocio de cuentas y movimientos (validación de pertenencia, transferencias)."""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cuenta, Ingreso, Transaccion

CATEGORIA_TRANSFERENCIA = "Transferencia"
MEDIO_TRANSFERENCIA = "Transferencia Interna"


async def cuenta_propia(session: AsyncSession, usuario_id: int, cuenta_id: int) -> Cuenta:
    """Anti-IDOR: toda referencia a cuenta_id se valida contra el usuario. 404 si no es suya."""
    cuenta = await session.scalar(
        select(Cuenta).where(
            Cuenta.id == cuenta_id,
            Cuenta.usuario_id == usuario_id,
            Cuenta.activa.is_(True),
        )
    )
    if cuenta is None:
        raise HTTPException(status_code=404, detail="cuenta_no_encontrada")
    return cuenta


async def crear_transferencia(
    session: AsyncSession, usuario_id: int, origen_id: int, destino_id: int, monto: Decimal
) -> dict:
    """Par gasto+ingreso con categoria='Transferencia' en la misma transacción.

    Replica la semántica del bot (db.py registrar_transferencia): el par se excluye
    de los totales de gasto/ingreso pero sí afecta el saldo de cada cuenta.
    """
    if origen_id == destino_id:
        raise HTTPException(status_code=400, detail="cuentas_iguales")
    origen = await cuenta_propia(session, usuario_id, origen_id)
    destino = await cuenta_propia(session, usuario_id, destino_id)

    gasto = Transaccion(
        usuario_id=usuario_id,
        monto=monto,
        medio=MEDIO_TRANSFERENCIA,
        descripcion=f"Transferencia a {destino.nombre}",
        categoria=CATEGORIA_TRANSFERENCIA,
        cuenta_id=origen.id,
    )
    ingreso = Ingreso(
        usuario_id=usuario_id,
        monto=monto,
        descripcion=f"Transferencia desde {origen.nombre}",
        categoria=CATEGORIA_TRANSFERENCIA,
        cuenta_id=destino.id,
    )
    session.add_all([gasto, ingreso])
    await session.flush()
    return {"gasto_id": gasto.id, "ingreso_id": ingreso.id, "monto": monto}
