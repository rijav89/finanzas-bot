"""Reportes: los mismos movimientos agrupados por la dimensión que se pida.

Gastos e ingresos viven en tablas distintas, así que todo parte de un UNION con una
etiqueta de tipo. Cada fila del reporte trae las dos columnas —lo que entró y lo que
salió— porque agrupar por mes y ver solo un total escondería justamente el mes en que
entró mucho y salió más.
"""
from datetime import date, datetime, time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constantes import SQL_EXCLUIR_SIN_TOTALES

Agrupacion = ("categoria", "mes", "cuenta")

#: Tope de filas del detalle exportado. El servidor tiene 350 MB y un reporte de
#: cinco años entero en memoria no vale el riesgo de que se caiga la API.
MAX_FILAS_DETALLE = 5000


def _clave(group_by: str, dialecto: str) -> str:
    if group_by == "categoria":
        return "COALESCE(m.categoria, 'Sin categoría')"
    if group_by == "cuenta":
        return "COALESCE(c.nombre, 'Sin cuenta')"
    # Mes: cada motor tiene su propia forma de recortar una fecha
    return (
        "to_char(m.fecha, 'YYYY-MM')"
        if dialecto == "postgresql"
        else "strftime('%Y-%m', m.fecha)"
    )


def _union(usuario_id: int, filtros: dict) -> tuple[str, dict]:
    """Sub-consulta con gastos e ingresos homogéneos, ya filtrados."""
    condiciones = [
        "usuario_id = :uid",
        SQL_EXCLUIR_SIN_TOTALES,
        "fecha >= :desde",
        "fecha < :hasta",
    ]
    params: dict = {
        "uid": usuario_id,
        "desde": filtros["desde"],
        "hasta": filtros["hasta"],
    }
    if filtros.get("categoria"):
        condiciones.append("categoria = :categoria")
        params["categoria"] = filtros["categoria"]
    if filtros.get("cuenta_id"):
        condiciones.append("cuenta_id = :cuenta_id")
        params["cuenta_id"] = filtros["cuenta_id"]

    donde = " AND ".join(condiciones)
    tipo = filtros.get("tipo")
    ramas = []
    if tipo in (None, "gasto"):
        ramas.append(
            "SELECT id, 'gasto' AS tipo, monto, categoria, descripcion, fecha, cuenta_id "
            f"FROM transacciones WHERE {donde}"
        )
    if tipo in (None, "ingreso"):
        ramas.append(
            "SELECT id, 'ingreso' AS tipo, monto, categoria, descripcion, fecha, cuenta_id "
            f"FROM ingresos WHERE {donde}"
        )
    return " UNION ALL ".join(ramas), params


def limites(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """`hasta` es inclusivo para quien lo elige, exclusivo para la consulta."""
    return datetime.combine(desde, time.min), datetime.combine(hasta, time.max)


async def resumen(
    session: AsyncSession,
    usuario_id: int,
    *,
    desde: date,
    hasta: date,
    group_by: str = "categoria",
    tipo: str | None = None,
    categoria: str | None = None,
    cuenta_id: int | None = None,
) -> dict:
    d, h = limites(desde, hasta)
    filtros = {
        "desde": d, "hasta": h, "tipo": tipo,
        "categoria": categoria, "cuenta_id": cuenta_id,
    }
    union, params = _union(usuario_id, filtros)
    clave = _clave(group_by, session.bind.dialect.name)

    sql = text(f"""
        SELECT {clave} AS clave,
               COALESCE(SUM(CASE WHEN m.tipo = 'gasto' THEN m.monto ELSE 0 END), 0) AS gastos,
               COALESCE(SUM(CASE WHEN m.tipo = 'ingreso' THEN m.monto ELSE 0 END), 0) AS ingresos,
               COUNT(*) AS n
        FROM ({union}) m
        LEFT JOIN cuentas c ON c.id = m.cuenta_id
        GROUP BY {clave}
        ORDER BY {"clave" if group_by == "mes" else "gastos DESC, ingresos DESC"}
    """)

    filas = [
        {
            "clave": r.clave,
            "gastos": float(r.gastos),
            "ingresos": float(r.ingresos),
            "neto": round(float(r.ingresos) - float(r.gastos), 2),
            "n": r.n,
        }
        for r in (await session.execute(sql, params)).all()
    ]

    return {
        "periodo": {"desde": desde, "hasta": hasta},
        "group_by": group_by,
        "filtros": {"tipo": tipo, "categoria": categoria, "cuenta_id": cuenta_id},
        "filas": filas,
        "totales": {
            "gastos": round(sum(f["gastos"] for f in filas), 2),
            "ingresos": round(sum(f["ingresos"] for f in filas), 2),
            "neto": round(sum(f["neto"] for f in filas), 2),
            "n": sum(f["n"] for f in filas),
        },
    }


async def detalle(
    session: AsyncSession,
    usuario_id: int,
    *,
    desde: date,
    hasta: date,
    tipo: str | None = None,
    categoria: str | None = None,
    cuenta_id: int | None = None,
    limite: int = MAX_FILAS_DETALLE,
) -> list[dict]:
    """Movimiento por movimiento, para las hojas de detalle de los archivos."""
    d, h = limites(desde, hasta)
    union, params = _union(
        usuario_id,
        {"desde": d, "hasta": h, "tipo": tipo, "categoria": categoria, "cuenta_id": cuenta_id},
    )
    params["limite"] = limite

    sql = text(f"""
        SELECT m.fecha, m.tipo, m.monto, m.categoria, m.descripcion, c.nombre AS cuenta
        FROM ({union}) m
        LEFT JOIN cuentas c ON c.id = m.cuenta_id
        ORDER BY m.fecha DESC, m.id DESC
        LIMIT :limite
    """)
    return [
        {
            "fecha": r.fecha,
            "tipo": r.tipo,
            "monto": float(r.monto),
            "categoria": r.categoria,
            "descripcion": r.descripcion,
            "cuenta": r.cuenta,
        }
        for r in (await session.execute(sql, params)).all()
    ]
