"""Lectura de los insights que dejó el job semanal. Cero IA en el request path."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, get_db_lectura, require_csrf
from app.models import InsightIA
from app.schemas.common import ok
from app.schemas.insights import MarcarLeido

router = APIRouter(prefix="/insights", tags=["insights"], dependencies=[Depends(require_csrf)])

#: Lo urgente primero; dentro de cada nivel, lo más reciente.
_ORDEN_SEVERIDAD = case(
    {"critico": 0, "atencion": 1, "info": 2}, value=InsightIA.severidad, else_=3
)


def _serializar(i: InsightIA) -> dict:
    payload = i.payload or {}
    return {
        "id": i.id,
        "tipo": i.tipo,
        "severidad": i.severidad,
        "titulo": i.titulo,
        "detalle": payload.get("detalle"),
        "categoria": payload.get("categoria"),
        "metrica": payload.get("metrica"),
        "delta_pct": payload.get("delta_pct"),
        "periodo_inicio": i.periodo_inicio,
        "periodo_fin": i.periodo_fin,
        "leido": i.leido,
        "creado_en": i.creado_en,
    }


@router.get("")
async def listar(
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_lectura),
    limite: int = Query(default=10, ge=1, le=50),
):
    filas = (
        await db.scalars(
            select(InsightIA)
            .where(InsightIA.usuario_id == user.usuario_id)
            .order_by(InsightIA.periodo_fin.desc(), _ORDEN_SEVERIDAD, InsightIA.id)
            .limit(limite)
        )
    ).all()
    items = [_serializar(i) for i in filas]
    return ok(
        {
            "items": items,
            "sin_leer": sum(1 for i in items if not i["leido"]),
            # Null mientras el job no haya corrido nunca: la UI lo dice explícito
            "generado_en": items[0]["creado_en"] if items else None,
        }
    )


@router.patch("/{insight_id}")
async def marcar(
    insight_id: int,
    body: MarcarLeido,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    insight = await db.scalar(
        select(InsightIA).where(
            InsightIA.id == insight_id, InsightIA.usuario_id == user.usuario_id
        )
    )
    if insight is None:
        raise HTTPException(status_code=404, detail="insight_no_encontrado")
    insight.leido = body.leido
    await db.flush()
    return ok(_serializar(insight))
