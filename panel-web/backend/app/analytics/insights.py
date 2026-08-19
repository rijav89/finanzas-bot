"""Pre-agregación de los datos que ve el modelo al generar insights.

El modelo nunca toca la base: recibe un resumen ya calculado, de ~40 números. Eso
mantiene el prompt en menos de 1.000 tokens, hace la salida reproducible y evita que
una alucinación se cuele como si fuera un dato.

Las ventanas de mes se calculan en Python y las queries filtran por rango, así que
todo esto corre igual en PostgreSQL y en SQLite (los tests).
"""
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.saldos import limites_mes
from app.core.constantes import SQL_EXCLUIR_SIN_TOTALES

#: Meses de historia que se le muestran al modelo, contando el actual.
MESES_HISTORIA = 4

_TOTALES = text(f"""
    SELECT
      COALESCE((SELECT SUM(monto) FROM transacciones WHERE usuario_id = :uid
                AND {SQL_EXCLUIR_SIN_TOTALES} AND fecha >= :desde AND fecha < :hasta), 0) AS gastos,
      COALESCE((SELECT SUM(monto) FROM ingresos WHERE usuario_id = :uid
                AND {SQL_EXCLUIR_SIN_TOTALES} AND fecha >= :desde AND fecha < :hasta), 0) AS ingresos
""")

_POR_CATEGORIA = text(f"""
    SELECT categoria, SUM(monto) AS total, COUNT(*) AS n
    FROM transacciones
    WHERE usuario_id = :uid AND {SQL_EXCLUIR_SIN_TOTALES}
      AND fecha >= :desde AND fecha < :hasta
    GROUP BY categoria
    ORDER BY total DESC
""")

_PRESUPUESTOS = text(f"""
    SELECT p.categoria, p.monto_limite,
           COALESCE((SELECT SUM(t.monto) FROM transacciones t
                     WHERE t.usuario_id = :uid AND t.categoria = p.categoria
                       AND {SQL_EXCLUIR_SIN_TOTALES}
                       AND t.fecha >= :desde AND t.fecha < :hasta), 0) AS gastado
    FROM presupuestos p
    WHERE p.usuario_id = :uid AND p.anio = :anio AND p.mes = :mes
""")

_SALDO = text("""
    SELECT COALESCE(SUM(
        COALESCE(c.saldo_inicial, 0)
        + COALESCE((SELECT SUM(i.monto) FROM ingresos i WHERE i.cuenta_id = c.id), 0)
        - COALESCE((SELECT SUM(t.monto) FROM transacciones t WHERE t.cuenta_id = c.id), 0)
    ), 0) AS saldo
    FROM cuentas c WHERE c.usuario_id = :uid AND c.activa
""")

_DEUDAS = text("""
    SELECT COALESCE(SUM(d.monto_total), 0)
         - COALESCE((SELECT SUM(q.monto) FROM cuotas_deuda q
                     JOIN deudas d2 ON d2.id = q.deuda_id
                     WHERE d2.usuario_id = :uid AND d2.estado = 'activa' AND q.pagada), 0)
         AS pendiente
    FROM deudas d
    WHERE d.usuario_id = :uid AND d.estado = 'activa'
      AND d.tipo IN ('prestamo_recibido', 'tarjeta')
""")

_RECURRENTES = text("""
    SELECT COALESCE(SUM(monto), 0) AS total, COUNT(*) AS n
    FROM pagos_fijos
    WHERE usuario_id = :uid AND activo AND frecuencia = 'mensual'
""")

#: Debajo de esto no hay nada que analizar y la llamada al modelo sería tokens tirados.
MINIMO_MOVIMIENTOS = 8


def meses_hacia_atras(hoy: date, cantidad: int) -> list[tuple[int, int]]:
    """Los últimos `cantidad` meses como (año, mes), del más viejo al actual."""
    indice = hoy.year * 12 + (hoy.month - 1)
    return [((indice - i) // 12, (indice - i) % 12 + 1) for i in range(cantidad - 1, -1, -1)]


async def datos_para_insights(session: AsyncSession, usuario_id: int, hoy: date) -> dict | None:
    """Devuelve None si el usuario todavía no tiene historia suficiente."""
    meses = meses_hacia_atras(hoy, MESES_HISTORIA)

    historia = []
    movimientos = 0
    for anio, mes in meses:
        desde, hasta = limites_mes(anio, mes)
        params = {"uid": usuario_id, "desde": desde, "hasta": hasta}
        totales = (await session.execute(_TOTALES, params)).one()
        categorias = (await session.execute(_POR_CATEGORIA, params)).all()
        movimientos += sum(c.n for c in categorias)
        historia.append(
            {
                "anio": anio,
                "mes": mes,
                "gastos": float(totales.gastos),
                "ingresos": float(totales.ingresos),
                "por_categoria": {c.categoria: float(c.total) for c in categorias},
            }
        )

    if movimientos < MINIMO_MOVIMIENTOS:
        return None

    actual = historia[-1]
    previos = historia[:-1]

    # Promedio por categoría de los meses anteriores: es la referencia contra la que
    # se mide si un gasto del mes se disparó
    promedio: dict[str, float] = {}
    if previos:
        for h in previos:
            for cat, total in h["por_categoria"].items():
                promedio[cat] = promedio.get(cat, 0.0) + total
        promedio = {c: round(t / len(previos), 2) for c, t in promedio.items()}

    anio, mes = meses[-1]
    desde, hasta = limites_mes(anio, mes)
    presupuestos = [
        {
            "categoria": p.categoria,
            "limite": float(p.monto_limite),
            "gastado": float(p.gastado),
        }
        for p in (
            await session.execute(
                _PRESUPUESTOS,
                {"uid": usuario_id, "desde": desde, "hasta": hasta, "anio": anio, "mes": mes},
            )
        ).all()
    ]

    saldo = float(await session.scalar(_SALDO, {"uid": usuario_id}) or 0)
    deuda = await session.scalar(_DEUDAS, {"uid": usuario_id})
    recurrentes = (await session.execute(_RECURRENTES, {"uid": usuario_id})).one()

    # Toda cifra derivada se calcula acá, no en el modelo: cuando se le pide dividir
    # o promediar, el resultado a veces sale mal y suena igual de convincente.
    gasto_promedio = round(sum(h["gastos"] for h in historia) / len(historia), 2)
    colchon = round(saldo / gasto_promedio, 1) if gasto_promedio else None
    colchon_al_ritmo_actual = (
        round(saldo / actual["gastos"], 1) if actual["gastos"] else None
    )

    return {
        "periodo": {"desde": desde, "hasta": hasta},
        "historia": historia,
        "promedio_categorias_previos": promedio,
        "presupuestos": presupuestos,
        "saldo_total": saldo,
        "deuda_pendiente": float(deuda or 0),
        "recurrentes": {"total_mensual": float(recurrentes.total), "cantidad": recurrentes.n},
        "ahorro_mes": round(actual["ingresos"] - actual["gastos"], 2),
        "gasto_promedio_mensual": gasto_promedio,
        "meses_de_colchon": colchon,
        "meses_de_colchon_al_ritmo_actual": colchon_al_ritmo_actual,
    }
