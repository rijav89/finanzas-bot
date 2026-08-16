from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, require_csrf
from app.models import CuotaDeuda, Deuda, Transaccion
from app.schemas.common import ok
from app.schemas.modulos import DeudaCrear, DeudaEditar, PagarCuota
from app.services.movimientos import cuenta_propia

router = APIRouter(prefix="/deudas", tags=["deudas"], dependencies=[Depends(require_csrf)])

CENTAVO = Decimal("0.01")


def _cronograma(total: Decimal, n: int, inicio: date) -> list[tuple[int, Decimal, date]]:
    """Cuotas iguales; el redondeo sobrante se ajusta en la última para que sumen el total."""
    base = (total / n).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    cuotas = []
    acumulado = Decimal("0")
    for i in range(1, n + 1):
        monto = base if i < n else (total - acumulado)
        acumulado += monto
        mes = inicio.month - 1 + i
        anio = inicio.year + mes // 12
        mes = mes % 12 + 1
        # Día 31 en meses cortos → último día del mes
        from calendar import monthrange

        dia = min(inicio.day, monthrange(anio, mes)[1])
        cuotas.append((i, monto, date(anio, mes, dia)))
    return cuotas


async def _resumen(db: AsyncSession, deuda: Deuda) -> dict:
    pagado = await db.scalar(
        select(func.coalesce(func.sum(CuotaDeuda.monto), 0)).where(
            CuotaDeuda.deuda_id == deuda.id, CuotaDeuda.pagada.is_(True)
        )
    )
    pendientes = await db.scalar(
        select(func.count()).where(
            CuotaDeuda.deuda_id == deuda.id, CuotaDeuda.pagada.is_(False)
        )
    )
    proxima = await db.scalar(
        select(CuotaDeuda)
        .where(CuotaDeuda.deuda_id == deuda.id, CuotaDeuda.pagada.is_(False))
        .order_by(CuotaDeuda.numero)
        .limit(1)
    )
    total = float(deuda.monto_total)
    pagado_f = float(pagado or 0)
    return {
        "id": deuda.id,
        "tipo": deuda.tipo,
        "acreedor": deuda.acreedor,
        "monto_total": total,
        "tasa_interes": float(deuda.tasa_interes) if deuda.tasa_interes is not None else None,
        "num_cuotas": deuda.num_cuotas,
        "fecha_inicio": deuda.fecha_inicio,
        "estado": deuda.estado,
        "cuenta_id": deuda.cuenta_id,
        "pagado": pagado_f,
        "saldo_pendiente": total - pagado_f,
        "porcentaje_pagado": round(pagado_f / total * 100, 1) if total else 0.0,
        "cuotas_pendientes": pendientes or 0,
        "proxima_cuota": (
            {"numero": proxima.numero, "monto": float(proxima.monto), "vence_en": proxima.vence_en}
            if proxima
            else None
        ),
    }


@router.get("")
async def listar(
    user: UsuarioActual = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    deudas = (
        await db.scalars(
            select(Deuda)
            .where(Deuda.usuario_id == user.usuario_id)
            .order_by(Deuda.estado, Deuda.fecha_inicio.desc())
        )
    ).all()
    items = [await _resumen(db, d) for d in deudas]
    activas = [i for i in items if i["estado"] == "activa"]
    return ok(
        {
            "items": items,
            "total_pendiente": sum(i["saldo_pendiente"] for i in activas),
            # Lo que se debe (recibido/tarjeta) vs lo que te deben (otorgado)
            "debo": sum(
                i["saldo_pendiente"]
                for i in activas
                if i["tipo"] in ("prestamo_recibido", "tarjeta")
            ),
            "me_deben": sum(
                i["saldo_pendiente"] for i in activas if i["tipo"] == "prestamo_otorgado"
            ),
        }
    )


@router.get("/{deuda_id}")
async def detalle(
    deuda_id: int,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deuda = await _propia(db, user.usuario_id, deuda_id)
    cuotas = (
        await db.scalars(
            select(CuotaDeuda).where(CuotaDeuda.deuda_id == deuda.id).order_by(CuotaDeuda.numero)
        )
    ).all()
    datos = await _resumen(db, deuda)
    datos["cuotas"] = [
        {
            "numero": c.numero,
            "monto": float(c.monto),
            "vence_en": c.vence_en,
            "pagada": c.pagada,
            "transaccion_id": c.transaccion_id,
        }
        for c in cuotas
    ]
    return ok(datos)


@router.post("", status_code=201)
async def crear(
    body: DeudaCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.cuenta_id is not None:
        await cuenta_propia(db, user.usuario_id, body.cuenta_id)

    datos = body.model_dump(exclude={"generar_cuotas"})
    deuda = Deuda(usuario_id=user.usuario_id, **datos)
    db.add(deuda)
    await db.flush()

    if body.generar_cuotas and body.num_cuotas:
        db.add_all(
            [
                CuotaDeuda(deuda_id=deuda.id, numero=n, monto=m, vence_en=v)
                for n, m, v in _cronograma(body.monto_total, body.num_cuotas, body.fecha_inicio)
            ]
        )
        await db.flush()

    return ok(await _resumen(db, deuda))


@router.patch("/{deuda_id}")
async def editar(
    deuda_id: int,
    body: DeudaEditar,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deuda = await _propia(db, user.usuario_id, deuda_id)
    cambios = body.model_dump(exclude_unset=True)
    if cambios.get("cuenta_id") is not None:
        await cuenta_propia(db, user.usuario_id, cambios["cuenta_id"])
    for campo, valor in cambios.items():
        setattr(deuda, campo, valor)
    await db.flush()
    return ok(await _resumen(db, deuda))


@router.post("/{deuda_id}/cuotas/{numero}/pagar")
async def pagar_cuota(
    deuda_id: int,
    numero: int,
    body: PagarCuota,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marca la cuota como pagada y registra el gasto asociado en la misma transacción.

    Si era la última pendiente, la deuda pasa a 'pagada'.
    """
    deuda = await _propia(db, user.usuario_id, deuda_id)

    cuota = await db.scalar(
        select(CuotaDeuda)
        .where(CuotaDeuda.deuda_id == deuda.id, CuotaDeuda.numero == numero)
        .with_for_update()
    )
    if cuota is None:
        raise HTTPException(status_code=404, detail="cuota_no_encontrada")
    if cuota.pagada:
        raise HTTPException(status_code=409, detail="cuota_ya_pagada")

    cuenta_id = body.cuenta_id or deuda.cuenta_id
    if cuenta_id is None:
        raise HTTPException(status_code=400, detail="cuenta_requerida")
    await cuenta_propia(db, user.usuario_id, cuenta_id)

    # Un préstamo otorgado que te devuelven es un ingreso, no un gasto:
    # por ahora solo se registra el movimiento en el caso de deuda propia.
    gasto = None
    if deuda.tipo in ("prestamo_recibido", "tarjeta"):
        gasto = Transaccion(
            usuario_id=user.usuario_id,
            monto=cuota.monto,
            categoria="Finanzas",
            descripcion=f"Cuota {numero}/{deuda.num_cuotas or '?'} — {deuda.acreedor}",
            medio="Pago de deuda",
            cuenta_id=cuenta_id,
            fecha=datetime.combine(body.fecha or date.today(), time(12, 0)),
        )
        db.add(gasto)
        await db.flush()

    cuota.pagada = True
    cuota.transaccion_id = gasto.id if gasto else None

    quedan = await db.scalar(
        select(func.count()).where(
            CuotaDeuda.deuda_id == deuda.id, CuotaDeuda.pagada.is_(False)
        )
    )
    if not quedan:
        deuda.estado = "pagada"
    await db.flush()

    return ok(
        {
            "cuota": numero,
            "transaccion_id": gasto.id if gasto else None,
            "deuda": await _resumen(db, deuda),
        }
    )


async def _propia(db: AsyncSession, usuario_id: int, deuda_id: int) -> Deuda:
    deuda = await db.scalar(
        select(Deuda).where(Deuda.id == deuda_id, Deuda.usuario_id == usuario_id)
    )
    if deuda is None:
        raise HTTPException(status_code=404, detail="deuda_no_encontrada")
    return deuda
