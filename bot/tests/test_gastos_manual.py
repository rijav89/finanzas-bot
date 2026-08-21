from gastos_manual import MEDIOS_DISPONIBLES, _validar


def test_medio_reconocido_se_normaliza():
    assert _validar("yape", MEDIOS_DISPONIBLES, None) == "Yape"


def test_medio_no_mencionado_devuelve_none():
    assert _validar(None, MEDIOS_DISPONIBLES, None) is None


def test_medio_invalido_devuelve_none():
    assert _validar("bitcoin", MEDIOS_DISPONIBLES, None) is None


def test_medio_con_mayusculas_distintas_se_normaliza():
    assert _validar("TARJETA", MEDIOS_DISPONIBLES, None) == "Tarjeta"
