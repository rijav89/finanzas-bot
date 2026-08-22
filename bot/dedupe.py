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
        try:
            monto = float(m.get("monto", 0))
        except (TypeError, ValueError):
            # Un monto que no se puede leer no puede coincidir con nada, pero
            # tampoco puede tumbar el lote entero: el usuario ve el movimiento
            # tildado y decide él. (ocr.normalizar_monto ya limpia lo que entra
            # por el camino normal; esto es el cinturón, no el tirante.)
            resultado.append(False)
            continue
        fecha = m.get("fecha")
        coincide = any(
            fecha == f_ex and abs(monto - m_ex) <= TOLERANCIA_MONTO
            for m_ex, f_ex in existentes
        )
        resultado.append(coincide)
    return resultado
