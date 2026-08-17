from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, get_db_lectura, require_csrf
from app.models import CuotaDeuda, Deuda, Ingreso, Transaccion
from app.schemas.common import ok
from app.schemas.modulos import DeudaCrear, DeudaEditar, MovimientoDeuda, PagarCuota
from app.services.movimientos import cuenta_propia

router = APIRouter(prefix="/deudas", tags=["deudas"], dependencies=[Depends(require_csrf)])

CENTAVO = Decimal("0.01")

#: Un préstamo entre personas no es ingreso ni gasto: la plata cambia de manos, no de
#: dueño. Con esta categoría el movimiento afecta el saldo pero queda fuera de los
#: totales del mes, igual que una transferencia.
CATEGORIA_PRESTAMO = "Prestamo"
#: La tarjeta sigue contando como gasto: sus compras ya se registraron una a una y
#: el tratamiento de créditos en cuotas quedó pendiente de decidir.
CATEGORIA_TARJETA = "Finanzas"


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


def _sale_de_mi_cuenta(tipo: str, *, momento: str) -> bool:
    """Dirección del dinero en cada momento del préstamo.

        momento      | me prestaron        | yo presté
        -------------|---------------------|---------------------
        desembolso   | entra               | sale
        saldar       | sale (devuelvo)     | entra (me devuelven)
    """
    if momento == "desembolso":
        return tipo == "prestamo_otorgado"
    return tipo != "prestamo_otorgado"


async def _mover_plata(
    db: AsyncSession,
    usuario_id: int,
    deuda: Deuda,
    monto: Decimal,
    cuenta_id: int,
    fecha: date | None,
    *,
    momento: str,
    descripcion: str,
) -> tuple[int | None, int | None]:
    """Registra el movimiento en la cuenta y devuelve (transaccion_id, ingreso_id)."""
    categoria = CATEGORIA_TARJETA if deuda.tipo == "tarjeta" else CATEGORIA_PRESTAMO
    cuando = datetime.combine(fecha or date.today(), time(12, 0))

    if _sale_de_mi_cuenta(deuda.tipo, momento=momento):
        mov = Transaccion(
            usuario_id=usuario_id,
            monto=monto,
            categoria=categoria,
            descripcion=descripcion,
            medio="Préstamo",
            cuenta_id=cuenta_id,
            fecha=cuando,
        )
        db.add(mov)
        await db.flush()
        return mov.id, None

    mov = Ingreso(
        usuario_id=usuario_id,
        monto=monto,
        categoria=categoria,
        descripcion=descripcion,
        cuenta_id=cuenta_id,
        fecha=cuando,
    )
    db.add(mov)
    await db.flush()
    return None, mov.id


async def _pagado(db: AsyncSession, deuda_id: int) -> Decimal:
    """Cuánto se saldó ya, sumando cuotas pagadas y devoluciones sueltas por igual."""
    total = await db.scalar(
        select(func.coalesce(func.sum(CuotaDeuda.monto), 0)).where(
            CuotaDeuda.deuda_id == deuda_id, CuotaDeuda.pagada.is_(True)
        )
    )
    return Decimal(str(total or 0))


async def _resumen(db: AsyncSession, deuda: Deuda) -> dict:
    pagado = await _pagado(db, deuda.id)
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
        # Sin cronograma: préstamo entre personas, se salda con montos sueltos
        "sin_cronograma": deuda.num_cuotas is None,
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
    user: UsuarioActual = Depends(get_current_user), db: AsyncSession = Depends(get_db_lectura)
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
    db: AsyncSession = Depends(get_db_lectura),
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
            "ingreso_id": c.ingreso_id,
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

    datos = body.model_dump(exclude={"generar_cuotas", "registrar_desembolso"})
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

    # El desembolso es el momento en que la plata cambia de manos. Sin esto la deuda
    # quedaba anotada pero el saldo de la cuenta no se enteraba.
    if body.registrar_desembolso and body.tipo != "tarjeta":
        if body.cuenta_id is None:
            raise HTTPException(status_code=400, detail="cuenta_requerida_para_desembolso")
        recibido = body.tipo == "prestamo_recibido"
        await _mover_plata(
            db,
            user.usuario_id,
            deuda,
            body.monto_total,
            body.cuenta_id,
            body.fecha_inicio,
            momento="desembolso",
            descripcion=(
                f"Préstamo de {deuda.acreedor}" if recibido else f"Préstamo a {deuda.acreedor}"
            ),
        )

    return ok(await _resumen(db, deuda))


@router.post("/{deuda_id}/movimientos", status_code=201)
async def registrar_movimiento(
    deuda_id: int,
    body: MovimientoDeuda,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devolución parcial o total de un préstamo sin cronograma.

    Entre personas se devuelve de a poco y cuando se puede, así que el monto lo pone
    quien registra. Cada movimiento queda como una fila de `cuotas_deuda` ya saldada,
    para que el avance de la deuda se calcule igual que en la vía de cuotas.
    """
    deuda = await _propia(db, user.usuario_id, deuda_id)

    cuenta_id = body.cuenta_id or deuda.cuenta_id
    if cuenta_id is None:
        raise HTTPException(status_code=400, detail="cuenta_requerida")
    await cuenta_propia(db, user.usuario_id, cuenta_id)

    pagado = await _pagado(db, deuda.id)
    if pagado + body.monto > deuda.monto_total:
        raise HTTPException(status_code=400, detail="monto_excede_lo_pendiente")

    devuelto = deuda.tipo == "prestamo_otorgado"
    transaccion_id, ingreso_id = await _mover_plata(
        db,
        user.usuario_id,
        deuda,
        body.monto,
        cuenta_id,
        body.fecha,
        momento="saldar",
        descripcion=(
            f"{deuda.acreedor} te devolvió" if devuelto else f"Devolución a {deuda.acreedor}"
        ),
    )

    ultimo = await db.scalar(
        select(func.coalesce(func.max(CuotaDeuda.numero), 0)).where(CuotaDeuda.deuda_id == deuda.id)
    )
    db.add(
        CuotaDeuda(
            deuda_id=deuda.id,
            numero=ultimo + 1,
            monto=body.monto,
            vence_en=body.fecha or date.today(),
            pagada=True,
            transaccion_id=transaccion_id,
            ingreso_id=ingreso_id,
        )
    )
    await db.flush()

    if await _pagado(db, deuda.id) >= deuda.monto_total:
        deuda.estado = "pagada"
    await db.flush()

    return ok(
        {
            "transaccion_id": transaccion_id,
            "ingreso_id": ingreso_id,
            "deuda": await _resumen(db, deuda),
        }
    )


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
    """Marca la cuota como saldada y registra el movimiento en la misma transacción.

    El movimiento sigue la dirección del préstamo: pagar una deuda propia genera un
    gasto, cobrar una que otorgaste genera un ingreso. Si era la última pendiente, la
    deuda pasa a 'pagada'.
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

    transaccion_id, ingreso_id = await _mover_plata(
        db,
        user.usuario_id,
        deuda,
        cuota.monto,
        cuenta_id,
        body.fecha,
        momento="saldar",
        descripcion=f"Cuota {numero}/{deuda.num_cuotas or '?'} — {deuda.acreedor}",
    )

    cuota.pagada = True
    cuota.transaccion_id = transaccion_id
    cuota.ingreso_id = ingreso_id

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
            "transaccion_id": transaccion_id,
            "ingreso_id": ingreso_id,
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
