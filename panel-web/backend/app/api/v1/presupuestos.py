from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, require_csrf
from app.models import Presupuesto
from app.schemas.common import ok
from app.schemas.modulos import PresupuestosUpsert

router = APIRouter(
    prefix="/presupuestos", tags=["presupuestos"], dependencies=[Depends(require_csrf)]
)

# Gasto real del periodo por categoría (excluye transferencias, igual que el bot)
_GASTADO_SQL = text("""
    SELECT categoria, SUM(monto) AS total
    FROM transacciones
    WHERE usuario_id = :uid
      AND categoria != 'Transferencia'
      AND fecha >= :desde AND fecha < :hasta
    GROUP BY categoria
""")


def _limites_mes(anio: int, mes: int) -> tuple[date, date]:
    desde = date(anio, mes, 1)
    hasta = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
    return desde, hasta


def _semaforo(gastado: float, limite: float) -> str:
    """Umbrales del panel: verde <80%, ámbar 80-100%, rojo >100%."""
    if limite <= 0:
        return "info"
    ratio = gastado / limite
    if ratio > 1:
        return "critico"
    if ratio >= 0.8:
        return "atencion"
    return "bien"


@router.get("")
async def listar(
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    anio: int | None = Query(default=None, ge=2020, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
):
    hoy = date.today()
    anio, mes = anio or hoy.year, mes or hoy.month
    desde, hasta = _limites_mes(anio, mes)

    presupuestos = (
        await db.scalars(
            select(Presupuesto)
            .where(
                Presupuesto.usuario_id == user.usuario_id,
                Presupuesto.anio == anio,
                Presupuesto.mes == mes,
            )
            .order_by(Presupuesto.categoria)
        )
    ).all()

    gastado_por_cat = {
        r.categoria: float(r.total)
        for r in (
            await db.execute(
                _GASTADO_SQL, {"uid": user.usuario_id, "desde": desde, "hasta": hasta}
            )
        ).all()
    }

    items = []
    for p in presupuestos:
        gastado = gastado_por_cat.get(p.categoria, 0.0)
        limite = float(p.monto_limite)
        items.append(
            {
                "id": p.id,
                "categoria": p.categoria,
                "monto_limite": limite,
                "gastado": gastado,
                "disponible": limite - gastado,
                "porcentaje": round(gastado / limite * 100, 1) if limite else 0.0,
                "semaforo": _semaforo(gastado, limite),
            }
        )

    # Categorías con gasto pero sin presupuesto definido: útiles para sugerir
    sin_presupuesto = [
        {"categoria": c, "gastado": g}
        for c, g in sorted(gastado_por_cat.items(), key=lambda kv: -kv[1])
        if c not in {p.categoria for p in presupuestos}
    ]

    return ok(
        {
            "periodo": {"anio": anio, "mes": mes},
            "items": items,
            "total_limite": sum(i["monto_limite"] for i in items),
            "total_gastado": sum(i["gastado"] for i in items),
            "sin_presupuesto": sin_presupuesto,
        }
    )


@router.put("")
async def upsert(
    body: PresupuestosUpsert,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reemplaza el set completo del periodo: lo que no venga en `items` se borra."""
    await db.execute(
        delete(Presupuesto).where(
            Presupuesto.usuario_id == user.usuario_id,
            Presupuesto.anio == body.anio,
            Presupuesto.mes == body.mes,
        )
    )
    # Última ocurrencia gana si el cliente manda la categoría repetida
    unicos = {i.categoria: i.monto_limite for i in body.items}
    db.add_all(
        [
            Presupuesto(
                usuario_id=user.usuario_id,
                categoria=cat,
                anio=body.anio,
                mes=body.mes,
                monto_limite=limite,
            )
            for cat, limite in unicos.items()
        ]
    )
    await db.flush()
    return ok({"guardados": len(unicos)})
