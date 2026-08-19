"""Queries analíticas del dashboard — raw SQL parametrizado.

Reglas heredadas del bot:
- 'Transferencia' y 'Prestamo' (ver `core.constantes.CATEGORIAS_SIN_TOTALES`) se
  excluyen de los totales de gasto/ingreso, pero SÍ afectan los saldos por cuenta:
  mueven plata sin que sea algo que ganaste ni gastaste.
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
                WHERE t.usuario_id = :uid AND t.categoria NOT IN ('Transferencia', 'Prestamo')
                  AND t.fecha >= :desde AND t.fecha < :hasta), 0) AS gastos,

      COALESCE((SELECT SUM(i.monto) FROM ingresos i
                WHERE i.usuario_id = :uid AND i.categoria NOT IN ('Transferencia', 'Prestamo')
                  AND i.fecha >= :desde AND i.fecha < :hasta), 0) AS ingresos,

      COALESCE((
        SELECT json_agg(y ORDER BY y.total DESC)
        FROM (
          SELECT t.categoria, SUM(t.monto) AS total, COUNT(*) AS n
          FROM transacciones t
          WHERE t.usuario_id = :uid AND t.categoria NOT IN ('Transferencia', 'Prestamo')
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
          WHERE i.usuario_id = :uid AND i.categoria NOT IN ('Transferencia', 'Prestamo')
            AND i.fecha >= :desde AND i.fecha < :hasta
          GROUP BY i.categoria
        ) z
      ), '[]'::json) AS ingresos_por_categoria,

      -- Widget «Últimos registros»: gastos e ingresos mezclados, los 5 más recientes
      COALESCE((
        SELECT json_agg(u ORDER BY u.fecha DESC, u.id DESC)
        FROM (
          SELECT * FROM (
            SELECT t.id, 'gasto' AS tipo, t.monto, t.categoria, t.descripcion,
                   t.fecha, c.nombre AS cuenta
            FROM transacciones t
            LEFT JOIN cuentas c ON c.id = t.cuenta_id
            WHERE t.usuario_id = :uid AND t.categoria NOT IN ('Transferencia', 'Prestamo')
            UNION ALL
            SELECT i.id, 'ingreso' AS tipo, i.monto, i.categoria, i.descripcion,
                   i.fecha, c.nombre AS cuenta
            FROM ingresos i
            LEFT JOIN cuentas c ON c.id = i.cuenta_id
            WHERE i.usuario_id = :uid AND i.categoria NOT IN ('Transferencia', 'Prestamo')
          ) mezcla
          ORDER BY fecha DESC, id DESC
          LIMIT 5
        ) u
      ), '[]'::json) AS ultimos_movimientos,

      -- Referencia de las pastillas «vs promedio»: meses previos, sin contar el actual
      COALESCE((SELECT SUM(t.monto) FROM transacciones t
                WHERE t.usuario_id = :uid AND t.categoria NOT IN ('Transferencia', 'Prestamo')
                  AND t.fecha >= :prev_desde AND t.fecha < :desde), 0) AS gastos_previos,

      COALESCE((SELECT SUM(i.monto) FROM ingresos i
                WHERE i.usuario_id = :uid AND i.categoria NOT IN ('Transferencia', 'Prestamo')
                  AND i.fecha >= :prev_desde AND i.fecha < :desde), 0) AS ingresos_previos,

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
            -- CAST y no la forma corta con doble dos-puntos: text() no reconoce
            -- un bind seguido de ':' y lo dejaría literal en la consulta.
            SELECT g AS mes, g + interval '1 month' AS corte
            FROM generate_series(
              CAST(:tend_desde AS date), CAST(:desde AS date), interval '1 month'
            ) g
          ) m
        ) s
      ), '[]'::json) AS tendencia_saldo
""")

# Meses que muestra el gráfico de tendencia, contando el mes en curso.
MESES_TENDENCIA = 6

#: Meses previos que promedian las pastillas «vs promedio». Tres es suficiente para
#: que un mes raro no defina la referencia, y corto para que siga siendo tu presente.
MESES_PROMEDIO = 3


def limites_mes(anio: int, mes: int) -> tuple[date, date]:
    desde = date(anio, mes, 1)
    hasta = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
    return desde, hasta


def _restar_meses(desde: date, meses: int) -> date:
    total = desde.year * 12 + (desde.month - 1) - meses
    return date(total // 12, total % 12 + 1, 1)


def inicio_ventana_tendencia(desde: date) -> date:
    """Primer mes del gráfico de tendencia, contando `desde` como el último."""
    return _restar_meses(desde, MESES_TENDENCIA - 1)


async def resumen_dashboard(session: AsyncSession, usuario_id: int, anio: int, mes: int) -> dict:
    desde, hasta = limites_mes(anio, mes)
    params = {
        "uid": usuario_id,
        "desde": desde,
        "hasta": hasta,
        "tend_desde": inicio_ventana_tendencia(desde),
        "prev_desde": _restar_meses(desde, MESES_PROMEDIO),
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
        "ultimos_movimientos": fila.ultimos_movimientos or [],
        "tendencia_saldo": fila.tendencia_saldo or [],
        "promedio_previos": _promedios(fila.gastos_previos, fila.ingresos_previos),
    }


def _promedios(gastos_previos, ingresos_previos) -> dict:
    """Promedio mensual de los meses anteriores al actual.

    Cero significa «no hay con qué comparar», y la UI omite la pastilla en vez de
    mostrar un porcentaje contra cero.
    """
    return {
        "gastos": round(float(gastos_previos or 0) / MESES_PROMEDIO, 2),
        "ingresos": round(float(ingresos_previos or 0) / MESES_PROMEDIO, 2),
        "meses": MESES_PROMEDIO,
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
                AND categoria NOT IN ('Transferencia', 'Prestamo') AND fecha >= :desde AND fecha < :hasta), 0) AS gastos,
      COALESCE((SELECT SUM(monto) FROM ingresos WHERE usuario_id = :uid
                AND categoria NOT IN ('Transferencia', 'Prestamo') AND fecha >= :desde AND fecha < :hasta), 0) AS ingresos
""")

_CATEGORIAS_PORTABLE = text("""
    SELECT categoria, SUM(monto) AS total, COUNT(*) AS n
    FROM transacciones
    WHERE usuario_id = :uid AND categoria NOT IN ('Transferencia', 'Prestamo')
      AND fecha >= :desde AND fecha < :hasta
    GROUP BY categoria
    ORDER BY total DESC
""")

_CATEGORIAS_ING_PORTABLE = text("""
    SELECT categoria, SUM(monto) AS total, COUNT(*) AS n
    FROM ingresos
    WHERE usuario_id = :uid AND categoria NOT IN ('Transferencia', 'Prestamo')
      AND fecha >= :desde AND fecha < :hasta
    GROUP BY categoria
    ORDER BY total DESC
""")

_ULTIMOS_MOV_PORTABLE = text("""
    SELECT id, tipo, monto, categoria, descripcion, fecha, cuenta FROM (
      SELECT t.id, 'gasto' AS tipo, t.monto, t.categoria, t.descripcion,
             t.fecha, c.nombre AS cuenta
      FROM transacciones t
      LEFT JOIN cuentas c ON c.id = t.cuenta_id
      WHERE t.usuario_id = :uid AND t.categoria NOT IN ('Transferencia', 'Prestamo')
      UNION ALL
      SELECT i.id, 'ingreso' AS tipo, i.monto, i.categoria, i.descripcion,
             i.fecha, c.nombre AS cuenta
      FROM ingresos i
      LEFT JOIN cuentas c ON c.id = i.cuenta_id
      WHERE i.usuario_id = :uid AND i.categoria NOT IN ('Transferencia', 'Prestamo')
    ) mezcla
    ORDER BY fecha DESC, id DESC
    LIMIT 5
""")

_PREVIOS_PORTABLE = text("""
    SELECT
      COALESCE((SELECT SUM(monto) FROM transacciones WHERE usuario_id = :uid
                AND categoria NOT IN ('Transferencia', 'Prestamo')
                AND fecha >= :prev_desde AND fecha < :desde), 0) AS gastos,
      COALESCE((SELECT SUM(monto) FROM ingresos WHERE usuario_id = :uid
                AND categoria NOT IN ('Transferencia', 'Prestamo')
                AND fecha >= :prev_desde AND fecha < :desde), 0) AS ingresos
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
    ultimos_movimientos = [
        {
            "id": r.id,
            "tipo": r.tipo,
            "monto": r.monto,
            "categoria": r.categoria,
            "descripcion": r.descripcion,
            "fecha": r.fecha,
            "cuenta": r.cuenta,
        }
        for r in (await session.execute(_ULTIMOS_MOV_PORTABLE, {"uid": usuario_id})).all()
    ]
    previos = (await session.execute(_PREVIOS_PORTABLE, params)).one()

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
        "ultimos_movimientos": ultimos_movimientos,
        "tendencia_saldo": tendencia_saldo,
        "promedio_previos": _promedios(previos.gastos, previos.ingresos),
    }
