from dedupe import marcar_duplicados


def test_mismo_monto_y_fecha_marca_duplicado():
    movimientos = [{"monto": 32.0, "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [True]


def test_monto_distinto_no_marca():
    movimientos = [{"monto": 32.0, "fecha": "2026-08-18"}]
    existentes = [(50.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [False]


def test_fecha_distinta_no_marca():
    movimientos = [{"monto": 32.0, "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-17")]
    assert marcar_duplicados(movimientos, existentes) == [False]


def test_tolerancia_de_un_centavo():
    movimientos = [{"monto": 32.005, "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [True]


def test_diferencia_de_dos_centavos_no_marca():
    movimientos = [{"monto": 32.02, "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [False]


def test_lote_mixto_evalua_cada_uno_independiente():
    movimientos = [
        {"monto": 32.0, "fecha": "2026-08-18"},
        {"monto": 10.0, "fecha": "2026-08-14"},
    ]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [True, False]


def test_sin_existentes_nada_se_marca():
    movimientos = [{"monto": 32.0, "fecha": "2026-08-18"}]
    assert marcar_duplicados(movimientos, []) == [False]


# ── Montos como los entrega el OCR (strings, no floats) ─────────────────────
# En producción `marcar_duplicados` nunca recibe floats: recibe los dicts que
# salen de ocr._normalizar, donde "monto" es un string.

def test_monto_string_del_ocr_marca_duplicado():
    movimientos = [{"monto": "32.00", "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [True]


def test_monto_string_ya_normalizado_con_miles_marca_duplicado():
    """El string sucio ("1,250.00") lo limpia ocr.normalizar_monto antes de
    llegar acá; lo que dedupe ve siempre es la forma canónica."""
    from ocr import normalizar_monto

    movimientos = [{"monto": normalizar_monto("S/ 1,250.00"), "fecha": "2026-08-18"}]
    existentes = [(1250.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [True]


def test_monto_sucio_sin_normalizar_no_revienta_y_no_marca():
    """Contrato defensivo: si algún camino futuro se saltea la normalización,
    el lote NO debe morir con un ValueError a mitad del checklist. El movimiento
    queda sin marcar (el usuario lo ve tildado y decide él)."""
    movimientos = [{"monto": "1,250.00", "fecha": "2026-08-18"}]
    existentes = [(1250.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [False]


def test_monto_ausente_no_revienta():
    assert marcar_duplicados([{"fecha": "2026-08-18"}], [(0.0, "2026-08-18")]) == [True]
