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
