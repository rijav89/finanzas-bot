from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.saldos import resumen_dashboard
from app.core.deps import UsuarioActual, get_current_user, get_db
from app.schemas.common import ok

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen")
async def resumen(
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    anio: int | None = Query(default=None, ge=2020, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
):
    hoy = date.today()
    datos = await resumen_dashboard(db, user.usuario_id, anio or hoy.year, mes or hoy.month)
    return ok(datos)
