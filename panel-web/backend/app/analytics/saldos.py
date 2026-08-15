"""Queries analíticas del dashboard — raw SQL parametrizado.

Reglas heredadas del bot:
- 'Transferencia' se excluye de totales de gasto/ingreso, pero SÍ afecta saldos por cuenta.
- Saldo por cuenta = saldo_inicial + SUM(ingresos) - SUM(gastos) HISTÓRICO
  (corrige el bug del bot que resetea el saldo cada mes).
"""
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SALDOS_SQL = text("""
    SELECT c.id, c.nombre, c.tipo, c.es_principal,
           COALESCE(c.saldo_inicial, 0)
             + COALESCE((SELECT SUM(i.monto) FROM ingresos i
                         WHERE i.cuenta_id = c.id AND i.usuario_id = :uid), 0)
             - COALESCE((SELECT SUM(t.monto) FROM transacciones t
                         WHERE t.cuenta_id = c.id AND t.usuario_id = :uid), 0) AS saldo
    FROM cuentas c
    WHERE c.usuario_id = :uid AND c.activa
    ORDER BY c.es_principal DESC, c.nombre
""")

_TOTALES_MES_SQL = text("""
    SELECT
      COALESCE((SELECT SUM(t.monto) FROM transacciones t
                WHERE t.usuario_id = :uid
                  AND t.categoria != 'Transferencia'
                  AND t.fecha >= :desde AND t.fecha < :hasta), 0) AS gastos,
      COALESCE((SELECT SUM(i.monto) FROM ingresos i
                WHERE i.usuario_id = :uid
                  AND i.categoria != 'Transferencia'
                  AND i.fecha >= :desde AND i.fecha < :hasta), 0) AS ingresos
""")

_POR_CATEGORIA_SQL = text("""
    SELECT t.categoria, SUM(t.monto) AS total, COUNT(*) AS n
    FROM transacciones t
    WHERE t.usuario_id = :uid
      AND t.categoria != 'Transferencia'
      AND t.fecha >= :desde AND t.fecha < :hasta
    GROUP BY t.categoria
    ORDER BY total DESC
""")


def _limites_mes(anio: int, mes: int) -> tuple[date, date]:
    desde = date(anio, mes, 1)
    hasta = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
    return desde, hasta


async def resumen_dashboard(session: AsyncSession, usuario_id: int, anio: int, mes: int) -> dict:
    desde, hasta = _limites_mes(anio, mes)

    saldos = [
        {
            "cuenta_id": r.id,
            "nombre": r.nombre,
            "tipo": r.tipo,
            "es_principal": bool(r.es_principal),
            "saldo": r.saldo,
        }
        for r in (await session.execute(_SALDOS_SQL, {"uid": usuario_id})).all()
    ]

    totales = (
        await session.execute(
            _TOTALES_MES_SQL, {"uid": usuario_id, "desde": desde, "hasta": hasta}
        )
    ).one()

    por_categoria = [
        {"categoria": r.categoria, "total": r.total, "n": r.n}
        for r in (
            await session.execute(
                _POR_CATEGORIA_SQL, {"uid": usuario_id, "desde": desde, "hasta": hasta}
            )
        ).all()
    ]

    return {
        "periodo": {"anio": anio, "mes": mes},
        "saldo_total": sum((s["saldo"] for s in saldos), start=0),
        "saldos_por_cuenta": saldos,
        "gastos_mes": totales.gastos,
        "ingresos_mes": totales.ingresos,
        "por_categoria": por_categoria,
    }
