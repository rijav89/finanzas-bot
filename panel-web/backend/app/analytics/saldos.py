"""Queries analíticas del dashboard — raw SQL parametrizado.

Reglas heredadas del bot:
- 'Transferencia' se excluye de totales de gasto/ingreso, pero SÍ afecta saldos por cuenta.
- Saldo por cuenta = saldo_inicial + SUM(ingresos) - SUM(gastos) HISTÓRICO
  (corrige el bug del bot que resetea el saldo cada mes).

Todo el resumen viaja en UNA sola consulta: a ~130 ms de RTT contra Supabase, cada
query extra se nota más que el trabajo que hace la base.
"""
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_RESUMEN_SQL = text("""
    SELECT
      COALESCE((
        SELECT json_agg(x ORDER BY x.es_principal DESC, x.nombre)
        FROM (
          SELECT c.id AS cuenta_id, c.nombre, c.tipo, c.es_principal,
                 COALESCE(c.saldo_inicial, 0)
                   + COALESCE((SELECT SUM(i.monto) FROM ingresos i
                               WHERE i.cuenta_id = c.id AND i.usuario_id = :uid), 0)
                   - COALESCE((SELECT SUM(t.monto) FROM transacciones t
                               WHERE t.cuenta_id = c.id AND t.usuario_id = :uid), 0) AS saldo
          FROM cuentas c
          WHERE c.usuario_id = :uid AND c.activa
        ) x
      ), '[]'::json) AS saldos,

      COALESCE((SELECT SUM(t.monto) FROM transacciones t
                WHERE t.usuario_id = :uid AND t.categoria != 'Transferencia'
                  AND t.fecha >= :desde AND t.fecha < :hasta), 0) AS gastos,

      COALESCE((SELECT SUM(i.monto) FROM ingresos i
                WHERE i.usuario_id = :uid AND i.categoria != 'Transferencia'
                  AND i.fecha >= :desde AND i.fecha < :hasta), 0) AS ingresos,

      COALESCE((
        SELECT json_agg(y ORDER BY y.total DESC)
        FROM (
          SELECT t.categoria, SUM(t.monto) AS total, COUNT(*) AS n
          FROM transacciones t
          WHERE t.usuario_id = :uid AND t.categoria != 'Transferencia'
            AND t.fecha >= :desde AND t.fecha < :hasta
          GROUP BY t.categoria
        ) y
      ), '[]'::json) AS por_categoria,

      -- Fuentes de ingreso del mes: alimentan el origen del diagrama de flujo
      COALESCE((
        SELECT json_agg(z ORDER BY z.total DESC)
        FROM (
          SELECT i.categoria, SUM(i.monto) AS total, COUNT(*) AS n
          FROM ingresos i
          WHERE i.usuario_id = :uid AND i.categoria != 'Transferencia'
            AND i.fecha >= :desde AND i.fecha < :hasta
          GROUP BY i.categoria
        ) z
      ), '[]'::json) AS ingresos_por_categoria,

      -- Widget «Últimos ingresos»: los más recientes, sin importar el mes en curso
      COALESCE((
        SELECT json_agg(u ORDER BY u.fecha DESC, u.id DESC)
        FROM (
          SELECT i.id, i.monto, i.categoria, i.descripcion, i.fecha, c.nombre AS cuenta
          FROM ingresos i
          LEFT JOIN cuentas c ON c.id = i.cuenta_id
          WHERE i.usuario_id = :uid AND i.categoria != 'Transferencia'
          ORDER BY i.fecha DESC, i.id DESC
          LIMIT 5
        ) u
      ), '[]'::json) AS ultimos_ingresos,

      -- Widget «Tendencia de saldo»: saldo al cierre de cada mes de la ventana.
      -- Las transferencias no se excluyen: a nivel global se netean solas.
      COALESCE((
        SELECT json_agg(s ORDER BY s.mes)
        FROM (
          SELECT m.mes::date AS mes,
                 (SELECT COALESCE(SUM(c.saldo_inicial), 0) FROM cuentas c
                  WHERE c.usuario_id = :uid AND c.activa)
                 + COALESCE((SELECT SUM(i.monto) FROM ingresos i
                             JOIN cuentas c ON c.id = i.cuenta_id
                             WHERE c.usuario_id = :uid AND c.activa AND i.fecha < m.corte), 0)
                 - COALESCE((SELECT SUM(t.monto) FROM transacciones t
                             JOIN cuentas c ON c.id = t.cuenta_id
                             WHERE c.usuario_id = :uid AND c.activa AND t.fecha < m.corte), 0)
                 AS saldo
          FROM (
            SELECT g AS mes, g + interval '1 month' AS corte
            FROM generate_series(:tend_desde::date, :desde::date, interval '1 month') g
          ) m
        ) s
      ), '[]'::json) AS tendencia_saldo
""")

# Meses que muestra el gráfico de tendencia, contando el mes en curso.
MESES_TENDENCIA = 6


def limites_mes(anio: int, mes: int) -> tuple[date, date]:
    desde = date(anio, mes, 1)
    hasta = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
    return desde, hasta


def inicio_ventana_tendencia(desde: date) -> date:
    """Primer mes del gráfico de tendencia, contando `desde` como el último."""
    total = desde.year * 12 + (desde.month - 1) - (MESES_TENDENCIA - 1)
    return date(total // 12, total % 12 + 1, 1)


async def resumen_dashboard(session: AsyncSession, usuario_id: int, anio: int, mes: int) -> dict:
    desde, hasta = limites_mes(anio, mes)
    params = {
        "uid": usuario_id,
        "desde": desde,
        "hasta": hasta,
        "tend_desde": inicio_ventana_tendencia(desde),
    }

    if session.bind.dialect.name != "postgresql":
        # SQLite (tests) no tiene json_agg ni generate_series: mismo resultado por partes.
        return await _resumen_portable(session, usuario_id, anio, mes, params)

    fila = (await session.execute(_RESUMEN_SQL, params)).one()
    saldos = fila.saldos or []
    return {
        "periodo": {"anio": anio, "mes": mes},
        "saldo_total": sum(float(s["saldo"]) for s in saldos),
        "saldos_por_cuenta": saldos,
        "gastos_mes": fila.gastos,
        "ingresos_mes": fila.ingresos,
        "por_categoria": fila.por_categoria or [],
        "ingresos_por_categoria": fila.ingresos_por_categoria or [],
        "ultimos_ingresos": fila.ultimos_ingresos or [],
        "tendencia_saldo": fila.tendencia_saldo or [],
    }


_SALDOS_PORTABLE = text("""
    SELECT c.id AS cuenta_id, c.nombre, c.tipo, c.es_principal,
           COALESCE(c.saldo_inicial, 0)
             + COALESCE((SELECT SUM(i.monto) FROM ingresos i
                         WHERE i.cuenta_id = c.id AND i.usuario_id = :uid), 0)
             - COALESCE((SELECT SUM(t.monto) FROM transacciones t
                         WHERE t.cuenta_id = c.id AND t.usuario_id = :uid), 0) AS saldo
    FROM cuentas c
    WHERE c.usuario_id = :uid AND c.activa
    ORDER BY c.es_principal DESC, c.nombre
""")

_TOTALES_PORTABLE = text("""
    SELECT
      COALESCE((SELECT SUM(monto) FROM transacciones WHERE usuario_id = :uid
                AND categoria != 'Transferencia' AND fecha >= :desde AND fecha < :hasta), 0) AS gastos,
      COALESCE((SELECT SUM(monto) FROM ingresos WHERE usuario_id = :uid
                AND categoria != 'Transferencia' AND fecha >= :desde AND fecha < :hasta), 0) AS ingresos
""")

_CATEGORIAS_PORTABLE = text("""
    SELECT categoria, SUM(monto) AS total, COUNT(*) AS n
    FROM transacciones
    WHERE usuario_id = :uid AND categoria != 'Transferencia'
      AND fecha >= :desde AND fecha < :hasta
    GROUP BY categoria
    ORDER BY total DESC
""")

_CATEGORIAS_ING_PORTABLE = text("""
    SELECT categoria, SUM(monto) AS total, COUNT(*) AS n
    FROM ingresos
    WHERE usuario_id = :uid AND categoria != 'Transferencia'
      AND fecha >= :desde AND fecha < :hasta
    GROUP BY categoria
    ORDER BY total DESC
""")

_ULTIMOS_ING_PORTABLE = text("""
    SELECT i.id, i.monto, i.categoria, i.descripcion, i.fecha, c.nombre AS cuenta
    FROM ingresos i
    LEFT JOIN cuentas c ON c.id = i.cuenta_id
    WHERE i.usuario_id = :uid AND i.categoria != 'Transferencia'
    ORDER BY i.fecha DESC, i.id DESC
    LIMIT 5
""")

_SALDO_AL_CORTE_PORTABLE = text("""
    SELECT (SELECT COALESCE(SUM(c.saldo_inicial), 0) FROM cuentas c
            WHERE c.usuario_id = :uid AND c.activa)
         + COALESCE((SELECT SUM(i.monto) FROM ingresos i
                     JOIN cuentas c ON c.id = i.cuenta_id
                     WHERE c.usuario_id = :uid AND c.activa AND i.fecha < :corte), 0)
         - COALESCE((SELECT SUM(t.monto) FROM transacciones t
                     JOIN cuentas c ON c.id = t.cuenta_id
                     WHERE c.usuario_id = :uid AND c.activa AND t.fecha < :corte), 0)
         AS saldo
""")


async def _resumen_portable(
    session: AsyncSession, usuario_id: int, anio: int, mes: int, params: dict
) -> dict:
    saldos = [
        {
            "cuenta_id": r.cuenta_id,
            "nombre": r.nombre,
            "tipo": r.tipo,
            "es_principal": bool(r.es_principal),
            "saldo": r.saldo,
        }
        for r in (await session.execute(_SALDOS_PORTABLE, {"uid": usuario_id})).all()
    ]
    totales = (await session.execute(_TOTALES_PORTABLE, params)).one()
    por_categoria = [
        {"categoria": r.categoria, "total": r.total, "n": r.n}
        for r in (await session.execute(_CATEGORIAS_PORTABLE, params)).all()
    ]
    ingresos_por_categoria = [
        {"categoria": r.categoria, "total": r.total, "n": r.n}
        for r in (await session.execute(_CATEGORIAS_ING_PORTABLE, params)).all()
    ]
    ultimos_ingresos = [
        {
            "id": r.id,
            "monto": r.monto,
            "categoria": r.categoria,
            "descripcion": r.descripcion,
            "fecha": r.fecha,
            "cuenta": r.cuenta,
        }
        for r in (await session.execute(_ULTIMOS_ING_PORTABLE, {"uid": usuario_id})).all()
    ]

    tendencia_saldo = []
    mes_ventana = inicio_ventana_tendencia(params["desde"])
    for _ in range(MESES_TENDENCIA):
        _, corte = limites_mes(mes_ventana.year, mes_ventana.month)
        saldo = await session.scalar(
            _SALDO_AL_CORTE_PORTABLE, {"uid": usuario_id, "corte": corte}
        )
        tendencia_saldo.append({"mes": mes_ventana, "saldo": saldo})
        mes_ventana = corte

    return {
        "periodo": {"anio": anio, "mes": mes},
        "saldo_total": sum(float(s["saldo"]) for s in saldos),
        "saldos_por_cuenta": saldos,
        "gastos_mes": totales.gastos,
        "ingresos_mes": totales.ingresos,
        "por_categoria": por_categoria,
        "ingresos_por_categoria": ingresos_por_categoria,
        "ultimos_ingresos": ultimos_ingresos,
        "tendencia_saldo": tendencia_saldo,
    }
