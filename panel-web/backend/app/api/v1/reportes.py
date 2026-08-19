"""Reportes con filtros y su exportación a Excel y PDF."""
import asyncio
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import reportes as analitica
from app.core.deps import UsuarioActual, get_current_user, get_db_lectura, require_csrf
from app.schemas.common import ok
from app.services import export

router = APIRouter(prefix="/reportes", tags=["reportes"], dependencies=[Depends(require_csrf)])

GroupBy = Literal["categoria", "mes", "cuenta"]
Tipo = Literal["gasto", "ingreso"]

#: Ventana máxima consultable. Más que esto no es un reporte, es un backup.
MAX_DIAS = 366 * 5


def _validar_rango(desde: date, hasta: date) -> None:
    if hasta < desde:
        raise HTTPException(status_code=400, detail="rango_invertido")
    if (hasta - desde).days > MAX_DIAS:
        raise HTTPException(status_code=400, detail="rango_demasiado_largo")


@router.get("/resumen")
async def resumen(
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_lectura),
    desde: date = Query(...),
    hasta: date = Query(...),
    group_by: GroupBy = "categoria",
    tipo: Tipo | None = None,
    categoria: str | None = Query(default=None, max_length=40),
    cuenta_id: int | None = None,
):
    _validar_rango(desde, hasta)
    datos = await analitica.resumen(
        db, user.usuario_id,
        desde=desde, hasta=hasta, group_by=group_by,
        tipo=tipo, categoria=categoria, cuenta_id=cuenta_id,
    )
    return ok(datos)


async def _armar(
    db: AsyncSession,
    usuario_id: int,
    formato: str,
    desde: date,
    hasta: date,
    group_by: str,
    tipo: str | None,
    categoria: str | None,
    cuenta_id: int | None,
) -> Response:
    _validar_rango(desde, hasta)

    # La reserva se toma antes de la primera consulta: si se tomara al armar el
    # archivo, un segundo pedido llegado mientras corren las queries se colaría.
    try:
        with export.reserva(usuario_id):
            return await _generar(
                db, usuario_id, formato, desde, hasta, group_by, tipo, categoria, cuenta_id
            )
    except export.ExportEnCurso:
        raise HTTPException(status_code=409, detail="export_en_curso") from None


async def _generar(
    db: AsyncSession,
    usuario_id: int,
    formato: str,
    desde: date,
    hasta: date,
    group_by: str,
    tipo: str | None,
    categoria: str | None,
    cuenta_id: int | None,
) -> Response:
    filtros = {"tipo": tipo, "categoria": categoria, "cuenta_id": cuenta_id}
    datos = await analitica.resumen(
        db, usuario_id, desde=desde, hasta=hasta, group_by=group_by, **filtros
    )
    movimientos = await analitica.detalle(
        db, usuario_id, desde=desde, hasta=hasta, **filtros
    )

    # Y un archivo por vez en todo el proceso, para que dos usuarios distintos no
    # sumen sus picos de memoria en una máquina de 1 GB.
    try:
        await asyncio.wait_for(export.turno().acquire(), timeout=20)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=429, detail="export_ocupado") from None

    try:
        # openpyxl y reportlab son sincrónicos: fuera del event loop
        constructor = export.excel if formato == "xlsx" else export.pdf
        contenido = await asyncio.to_thread(constructor, datos, movimientos)
    finally:
        export.turno().release()

    tipos_mime = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    }
    nombre = export.nombre_archivo(desde, hasta, formato)
    return Response(
        content=contenido,
        media_type=tipos_mime[formato],
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"',
            "Content-Length": str(len(contenido)),
        },
    )


@router.get("/export.xlsx")
async def export_excel(
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_lectura),
    desde: date = Query(...),
    hasta: date = Query(...),
    group_by: GroupBy = "categoria",
    tipo: Tipo | None = None,
    categoria: str | None = Query(default=None, max_length=40),
    cuenta_id: int | None = None,
):
    return await _armar(
        db, user.usuario_id, "xlsx", desde, hasta, group_by, tipo, categoria, cuenta_id
    )


@router.get("/export.pdf")
async def export_pdf(
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_lectura),
    desde: date = Query(...),
    hasta: date = Query(...),
    group_by: GroupBy = "categoria",
    tipo: Tipo | None = None,
    categoria: str | None = Query(default=None, max_length=40),
    cuenta_id: int | None = None,
):
    return await _armar(
        db, user.usuario_id, "pdf", desde, hasta, group_by, tipo, categoria, cuenta_id
    )
