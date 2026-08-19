"""Insights: pre-agregación, validación de la salida del modelo y lectura por API.

La llamada a Qwen no se prueba contra la red: lo que importa es que la basura que
pueda devolver no llegue nunca a la base ni a la pantalla.
"""
from datetime import date

import pytest

from tests.conftest import AUTH_UID_A, AUTH_UID_B, como

pytestmark = pytest.mark.asyncio


# ── Pre-agregación ───────────────────────────────────────────────────────────

async def test_meses_hacia_atras_cruza_el_anio():
    from app.analytics.insights import meses_hacia_atras

    assert meses_hacia_atras(date(2026, 2, 15), 4) == [
        (2025, 11), (2025, 12), (2026, 1), (2026, 2),
    ]


async def test_sin_historia_suficiente_no_gasta_tokens(cliente, datos, sesiones):
    """Con dos movimientos no hay nada que analizar: el job debe saltear al usuario."""
    from app.analytics.insights import datos_para_insights

    como(cliente, AUTH_UID_A)
    for _ in range(2):
        await cliente.post(
            "/api/v1/gastos",
            json={"monto": "10", "categoria": "Comida", "cuenta_id": datos["cuenta_a"]},
        )

    async with sesiones() as s:
        assert await datos_para_insights(s, datos["usuario_a"], date.today()) is None


async def test_datos_incluyen_categorias_presupuestos_y_saldo(cliente, datos, sesiones):
    from app.analytics.insights import MINIMO_MOVIMIENTOS, datos_para_insights

    como(cliente, AUTH_UID_A)
    await cliente.post(
        "/api/v1/ingresos", json={"monto": "3000", "cuenta_id": datos["cuenta_a"]}
    )
    for i in range(MINIMO_MOVIMIENTOS):
        await cliente.post(
            "/api/v1/gastos",
            json={
                "monto": "50",
                "categoria": "Comida" if i % 2 else "Transporte y vehiculo",
                "cuenta_id": datos["cuenta_a"],
            },
        )
    await cliente.put(
        "/api/v1/presupuestos",
        json={
            "anio": date.today().year,
            "mes": date.today().month,
            "items": [{"categoria": "Comida", "monto_limite": "100"}],
        },
    )

    async with sesiones() as s:
        d = await datos_para_insights(s, datos["usuario_a"], date.today())

    assert d is not None
    actual = d["historia"][-1]
    assert actual["por_categoria"]["Comida"] == 200.0
    assert d["saldo_total"] == 3000 - MINIMO_MOVIMIENTOS * 50
    assert d["presupuestos"] == [{"categoria": "Comida", "limite": 100.0, "gastado": 200.0}]
    assert d["ahorro_mes"] == 3000 - MINIMO_MOVIMIENTOS * 50

    # Las cifras derivadas se calculan acá y no en el modelo, que al dividir se equivoca
    gasto = MINIMO_MOVIMIENTOS * 50
    assert d["gasto_promedio_mensual"] == round(gasto / 4, 2)  # 4 meses de ventana
    assert d["meses_de_colchon"] == round(d["saldo_total"] / d["gasto_promedio_mensual"], 1)
    assert d["meses_de_colchon_al_ritmo_actual"] == round(d["saldo_total"] / gasto, 1)


async def test_prestamos_no_entran_en_los_datos_del_modelo(cliente, datos, sesiones):
    """Si un préstamo contara como gasto, el modelo escribiría un insight falso."""
    from app.analytics.insights import MINIMO_MOVIMIENTOS, datos_para_insights

    como(cliente, AUTH_UID_A)
    for _ in range(MINIMO_MOVIMIENTOS):
        await cliente.post(
            "/api/v1/gastos",
            json={"monto": "10", "categoria": "Comida", "cuenta_id": datos["cuenta_a"]},
        )
    await cliente.post(
        "/api/v1/deudas",
        json={
            "tipo": "prestamo_recibido",
            "acreedor": "Juan",
            "monto_total": "5000",
            "fecha_inicio": date.today().isoformat(),
            "cuenta_id": datos["cuenta_a"],
            "generar_cuotas": False,
        },
    )

    async with sesiones() as s:
        d = await datos_para_insights(s, datos["usuario_a"], date.today())

    assert d["historia"][-1]["ingresos"] == 0.0
    assert "Prestamo" not in d["historia"][-1]["por_categoria"]
    assert d["saldo_total"] == 5000 - MINIMO_MOVIMIENTOS * 10  # el saldo sí lo refleja


# ── Validación de la salida del modelo ───────────────────────────────────────

def _datos_minimos() -> dict:
    return {
        "periodo": {"desde": date(2026, 8, 1), "hasta": date(2026, 9, 1)},
        "historia": [
            {"anio": 2026, "mes": 8, "gastos": 500.0, "ingresos": 3000.0,
             "por_categoria": {"Comida": 500.0}}
        ],
        "promedio_categorias_previos": {"Comida": 250.0, "Ropa": 80.0},
        "presupuestos": [{"categoria": "Comida", "limite": 400.0, "gastado": 500.0}],
        "saldo_total": 2500.0,
        "deuda_pendiente": 0.0,
        "recurrentes": {"total_mensual": 120.0, "cantidad": 2},
        "ahorro_mes": 2500.0,
        "gasto_promedio_mensual": 500.0,
        "meses_de_colchon": 5.0,
        "meses_de_colchon_al_ritmo_actual": 5.0,
    }


async def test_el_resumen_le_da_al_modelo_las_cifras_y_la_comparacion():
    from app.services.insights_ia import formatear_resumen

    texto = formatear_resumen(_datos_minimos())
    assert "agosto 2026" in texto
    assert "S/ 500.00" in texto
    assert "+100%" in texto  # Comida duplicó su promedio
    assert "Ropa" in texto  # gastaba antes y este mes no: vale como señal
    assert "125%" in texto  # presupuesto excedido
    # El colchon va precalculado para que el modelo no tenga que dividir
    assert "alcanza para 5.0 meses" in texto
    # El rango del promedio va nombrado: deducirlo le sale mal
    assert "agosto a agosto 2026 (1 meses" in texto


async def test_respuesta_del_modelo_con_campos_de_mas_se_rechaza():
    from pydantic import ValidationError

    from app.schemas.insights import RespuestaInsights

    valido = {
        "insights": [
            {"tipo": "tendencia", "severidad": "atencion", "titulo": "Comida se duplicó",
             "detalle": "Gastaste S/ 500 contra un promedio de S/ 250 en los meses previos.",
             "categoria": "Comida", "metrica": "S/ 500.00", "delta_pct": 100.0}
        ]
    }
    assert len(RespuestaInsights(**valido).insights) == 1

    for roto in (
        {"insights": [{**valido["insights"][0], "inventado": "x"}]},
        {"insights": [{**valido["insights"][0], "severidad": "urgentisimo"}]},
        {"insights": [{**valido["insights"][0], "titulo": "no"}]},
        {"insights": [valido["insights"][0]] * 6},
    ):
        with pytest.raises(ValidationError):
            RespuestaInsights(**roto)


async def test_json_envuelto_en_markdown_se_limpia():
    from app.services.insights_ia import _limpiar

    assert _limpiar('```json\n{"insights": []}\n```') == '{"insights": []}'


# ── API ──────────────────────────────────────────────────────────────────────

async def _sembrar(sesiones, usuario_id: int, **campos):
    from app.models import InsightIA

    async with sesiones() as s:
        async with s.begin():
            s.add(
                InsightIA(
                    usuario_id=usuario_id,
                    tipo=campos.get("tipo", "tendencia"),
                    severidad=campos.get("severidad", "info"),
                    titulo=campos.get("titulo", "Un insight"),
                    periodo_inicio=date(2026, 8, 1),
                    periodo_fin=date(2026, 9, 1),
                    payload={"detalle": "Detalle.", "metrica": "S/ 10", "delta_pct": 5.0},
                    modelo="qwen-plus",
                    tokens_usados=900,
                )
            )


async def test_insights_llegan_ordenados_por_urgencia(cliente, datos, sesiones):
    await _sembrar(sesiones, datos["usuario_a"], severidad="info", titulo="Tranquilo")
    await _sembrar(sesiones, datos["usuario_a"], severidad="critico", titulo="Urgente")
    await _sembrar(sesiones, datos["usuario_a"], severidad="atencion", titulo="Mirá esto")

    como(cliente, AUTH_UID_A)
    d = (await cliente.get("/api/v1/insights")).json()["data"]

    assert [i["titulo"] for i in d["items"]] == ["Urgente", "Mirá esto", "Tranquilo"]
    assert d["sin_leer"] == 3
    assert d["items"][0]["detalle"] == "Detalle."


async def test_sin_insights_devuelve_lista_vacia(cliente, datos):
    como(cliente, AUTH_UID_A)
    d = (await cliente.get("/api/v1/insights")).json()["data"]
    assert d == {"items": [], "sin_leer": 0, "generado_en": None}


async def test_marcar_leido_y_no_ver_el_de_otro(cliente, datos, sesiones):
    await _sembrar(sesiones, datos["usuario_b"])

    como(cliente, AUTH_UID_B)
    ajeno = (await cliente.get("/api/v1/insights")).json()["data"]["items"][0]["id"]

    como(cliente, AUTH_UID_A)
    assert (await cliente.get("/api/v1/insights")).json()["data"]["items"] == []
    r = await cliente.patch(f"/api/v1/insights/{ajeno}", json={"leido": True})
    assert r.status_code == 404

    como(cliente, AUTH_UID_B)
    r = await cliente.patch(f"/api/v1/insights/{ajeno}", json={"leido": True})
    assert r.status_code == 200
    assert r.json()["data"]["leido"] is True
