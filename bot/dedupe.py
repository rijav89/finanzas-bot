"""
dedupe.py — FinanzasBot v3.1
Marca, sin tocar la base, qué movimientos de un lote importado ya podrían
estar registrados: mismo monto (±1 centavo) y misma fecha.

Deliberadamente NO compara texto/destinatario: dos fuentes distintas (una
captura de banco y lo que vos tipeaste a mano) casi nunca describen el mismo
movimiento con las mismas palabras, así que comparar texto da más falsos
negativos y positivos de los que evita.
"""

TOLERANCIA_MONTO = 0.01


def marcar_duplicados(movimientos: list[dict], existentes: list[tuple]) -> list[bool]:
    """True en la posición i si movimientos[i] coincide con algún existente.

    movimientos[i] necesita "monto" (float) y "fecha" ("YYYY-MM-DD").
    existentes es una lista de (monto: float, fecha: "YYYY-MM-DD") ya en la base.
    """
    resultado = []
    for m in movimientos:
        monto = float(m.get("monto", 0))
        fecha = m.get("fecha")
        coincide = any(
            fecha == f_ex and abs(monto - m_ex) <= TOLERANCIA_MONTO
            for m_ex, f_ex in existentes
        )
        resultado.append(coincide)
    return resultado
