from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, require_csrf
from app.models import PagoFijo
from app.schemas.common import ok
from app.schemas.modulos import RecurrenteCrear, RecurrenteEditar
from app.services.movimientos import cuenta_propia

router = APIRouter(
    prefix="/recurrentes", tags=["recurrentes"], dependencies=[Depends(require_csrf)]
)


def _proximo_vencimiento(dia_mes: int, frecuencia: str, hoy: date | None = None) -> date:
    """Próxima fecha de cobro. Ajusta el día al último del mes cuando no existe
    (ej. día 31 en abril) para no perder el pago."""
    hoy = hoy or date.today()
    if frecuencia == "semanal":
        return hoy  # el día del mes no aplica; el detalle fino llega con el job de F5

    anio, mes = hoy.year, hoy.month
    if frecuencia == "anual":
        candidato = date(anio, mes, min(dia_mes, monthrange(anio, mes)[1]))
        return candidato if candidato >= hoy else date(anio + 1, mes, dia_mes)

    candidato = date(anio, mes, min(dia_mes, monthrange(anio, mes)[1]))
    if candidato >= hoy:
        return candidato
    mes, anio = (1, anio + 1) if mes == 12 else (mes + 1, anio)
    return date(anio, mes, min(dia_mes, monthrange(anio, mes)[1]))


def _serializar(p: PagoFijo) -> dict:
    return {
        "id": p.id,
        "descripcion": p.descripcion,
        "monto": float(p.monto),
        "dia_mes": p.dia_mes,
        "categoria": p.categoria,
        "cuenta_id": p.cuenta_id,
        "frecuencia": p.frecuencia,
        "fecha_fin": p.fecha_fin,
        "activo": p.activo,
        "proximo_vencimiento": _proximo_vencimiento(p.dia_mes, p.frecuencia),
    }


@router.get("")
async def listar(
    user: UsuarioActual = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    filas = (
        await db.scalars(
            select(PagoFijo)
            .where(PagoFijo.usuario_id == user.usuario_id, PagoFijo.activo.is_(True))
            .order_by(PagoFijo.dia_mes)
        )
    ).all()
    items = [_serializar(p) for p in filas]
    return ok(
        {
            "items": items,
            "total_mensual": sum(
                i["monto"] for i in items if i["frecuencia"] == "mensual"
            ),
        }
    )


@router.post("", status_code=201)
async def crear(
    body: RecurrenteCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.cuenta_id is not None:
        await cuenta_propia(db, user.usuario_id, body.cuenta_id)
    pago = PagoFijo(usuario_id=user.usuario_id, **body.model_dump())
    db.add(pago)
    await db.flush()
    return ok(_serializar(pago))


@router.patch("/{pago_id}")
async def editar(
    pago_id: int,
    body: RecurrenteEditar,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pago = await _propio(db, user.usuario_id, pago_id)
    cambios = body.model_dump(exclude_unset=True)
    if cambios.get("cuenta_id") is not None:
        await cuenta_propia(db, user.usuario_id, cambios["cuenta_id"])
    for campo, valor in cambios.items():
        setattr(pago, campo, valor)
    await db.flush()
    return ok(_serializar(pago))


@router.delete("/{pago_id}")
async def desactivar(
    pago_id: int,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: el bot filtra por activo=TRUE en sus recordatorios."""
    pago = await _propio(db, user.usuario_id, pago_id)
    pago.activo = False
    return ok({"desactivado": True})


async def _propio(db: AsyncSession, usuario_id: int, pago_id: int) -> PagoFijo:
    pago = await db.scalar(
        select(PagoFijo).where(PagoFijo.id == pago_id, PagoFijo.usuario_id == usuario_id)
    )
    if pago is None:
        raise HTTPException(status_code=404, detail="recurrente_no_encontrado")
    return pago
