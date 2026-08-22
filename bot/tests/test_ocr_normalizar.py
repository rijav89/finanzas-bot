"""Normalización de lo que devuelve el modelo de OCR.

`_normalizar` es la única barrera entre un JSON escrito por un modelo y dos
consumidores que no toleran basura: `fecha` termina en un `BETWEEN` de SQL y en
un `strptime`, y `monto` en un `float()`. Ambos reventaban sin capturar.
"""
from datetime import date

import pytest

from ocr import _normalizar, normalizar_fecha, normalizar_monto

HOY = date.today().strftime("%Y-%m-%d")


# ── fecha ────────────────────────────────────────────────────────────────────

def test_fecha_iso_se_respeta():
    assert normalizar_fecha("2026-03-19") == "2026-03-19"


def test_fecha_iso_sin_ceros_se_completa():
    assert normalizar_fecha("2026-8-5") == "2026-08-05"


def test_fecha_peruana_dia_primero_se_convierte():
    assert normalizar_fecha("15/08/2026") == "2026-08-15"


def test_fecha_con_guiones_dia_primero_se_convierte():
    assert normalizar_fecha("15-08-2026") == "2026-08-15"


def test_fecha_no_detectada_cae_a_hoy():
    assert normalizar_fecha("No detectada") == HOY


def test_fecha_ilegible_cae_a_hoy():
    assert normalizar_fecha("ayer por la tarde") == HOY


def test_fecha_imposible_cae_a_hoy():
    assert normalizar_fecha("2026-02-31") == HOY


def test_fecha_vacia_o_nula_cae_a_hoy():
    assert normalizar_fecha("") == HOY
    assert normalizar_fecha(None) == HOY


# ── monto ────────────────────────────────────────────────────────────────────

def test_monto_limpio_se_normaliza_a_dos_decimales():
    assert normalizar_monto("85.5") == "85.50"


def test_monto_con_simbolo_de_soles():
    assert normalizar_monto("S/ 85.50") == "85.50"


def test_monto_con_separador_de_miles():
    assert normalizar_monto("1,250.00") == "1250.00"


def test_monto_con_formato_europeo():
    assert normalizar_monto("1.250,00") == "1250.00"


def test_monto_con_coma_decimal_sola():
    assert normalizar_monto("85,50") == "85.50"


def test_monto_con_coma_de_miles_sola():
    assert normalizar_monto("1,250") == "1250.00"


def test_monto_numerico_tambien_vale():
    assert normalizar_monto(1250) == "1250.00"


def test_monto_ilegible_queda_como_no_detectado():
    assert normalizar_monto("no se ve") == "No detectado"
    assert normalizar_monto("") == "No detectado"
    assert normalizar_monto(None) == "No detectado"


def test_monto_normalizado_es_apto_para_float():
    assert float(normalizar_monto("S/ 1,250.00")) == pytest.approx(1250.0)


# ── el diccionario completo ──────────────────────────────────────────────────

def test_normalizar_aplica_las_dos_limpiezas():
    salida = _normalizar({"monto": "S/ 1,250.00", "fecha": "15/08/2026"})
    assert salida["monto"] == "1250.00"
    assert salida["fecha"] == "2026-08-15"
    assert salida["medio"] == "No identificado"


def test_normalizar_no_pierde_los_campos_de_texto():
    salida = _normalizar({
        "monto": "32", "medio": "Yape", "destinatario": "Rosa",
        "descripcion": "Yape a Rosa", "fecha": "2026-08-18",
    })
    assert salida == {
        "monto": "32.00", "medio": "Yape", "destinatario": "Rosa",
        "descripcion": "Yape a Rosa", "fecha": "2026-08-18",
    }
