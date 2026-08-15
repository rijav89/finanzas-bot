"""Flujos funcionales: CRUD de movimientos, transferencia atómica y dashboard."""
import pytest

from tests.conftest import AUTH_UID_A, como

pytestmark = pytest.mark.asyncio


async def test_crear_gasto_y_listar(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/gastos",
        json={
            "monto": "45.50",
            "categoria": "Transporte",
            "cuenta_id": datos["cuenta_a"],
            "descripcion": "taxi aeropuerto",
        },
    )
    assert r.status_code == 201

    r = await cliente.get("/api/v1/movimientos", params={"q": "taxi"})
    items = r.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["tipo"] == "gasto"
    assert float(items[0]["monto"]) == 45.50


async def test_transferencia_crea_par_y_no_infla_totales(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/transferencias",
        json={
            "origen_id": datos["cuenta_a"],
            "destino_id": datos["cuenta_a2"],
            "monto": "100",
        },
    )
    assert r.status_code == 201

    r = await cliente.get("/api/v1/dashboard/resumen")
    d = r.json()["data"]
    # La transferencia no cuenta como gasto ni ingreso del mes...
    assert float(d["gastos_mes"]) == 0
    assert float(d["ingresos_mes"]) == 0
    # ...pero sí mueve los saldos entre cuentas
    saldos = {s["cuenta_id"]: float(s["saldo"]) for s in d["saldos_por_cuenta"]}
    assert saldos[datos["cuenta_a"]] == -100
    assert saldos[datos["cuenta_a2"]] == 100
    # y el saldo total del usuario queda neto en 0
    assert float(d["saldo_total"]) == 0


async def test_transferencia_misma_cuenta_400(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/transferencias",
        json={
            "origen_id": datos["cuenta_a"],
            "destino_id": datos["cuenta_a"],
            "monto": "10",
        },
    )
    assert r.status_code == 400


async def test_dashboard_saldo_historico_y_categorias(cliente, datos):
    como(cliente, AUTH_UID_A)
    await cliente.post(
        "/api/v1/ingresos",
        json={"monto": "1000", "cuenta_id": datos["cuenta_a"], "descripcion": "sueldo"},
    )
    await cliente.post(
        "/api/v1/gastos",
        json={"monto": "200", "categoria": "Comida", "cuenta_id": datos["cuenta_a"]},
    )
    await cliente.post(
        "/api/v1/gastos",
        json={"monto": "50", "categoria": "Comida", "cuenta_id": datos["cuenta_a"]},
    )

    r = await cliente.get("/api/v1/dashboard/resumen")
    d = r.json()["data"]
    assert float(d["ingresos_mes"]) == 1000
    assert float(d["gastos_mes"]) == 250
    saldos = {s["cuenta_id"]: float(s["saldo"]) for s in d["saldos_por_cuenta"]}
    assert saldos[datos["cuenta_a"]] == 750
    cat = {c["categoria"]: float(c["total"]) for c in d["por_categoria"]}
    assert cat["Comida"] == 250


async def test_editar_y_eliminar_movimiento_propio(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/gastos",
        json={"monto": "30", "categoria": "Otros", "cuenta_id": datos["cuenta_a"]},
    )
    gid = r.json()["data"]["id"]

    r = await cliente.patch(f"/api/v1/gastos/{gid}", json={"categoria": "Hogar"})
    assert r.status_code == 200

    r = await cliente.delete(f"/api/v1/gastos/{gid}")
    assert r.status_code == 200

    r = await cliente.get("/api/v1/movimientos")
    assert r.json()["data"]["items"] == []


async def test_monto_negativo_rechazado(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/gastos",
        json={"monto": "-5", "categoria": "Comida", "cuenta_id": datos["cuenta_a"]},
    )
    assert r.status_code == 422


async def test_cuenta_principal_no_archivable(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.delete(f"/api/v1/cuentas/{datos['cuenta_a']}")
    assert r.status_code == 400
    assert r.json()["error"] == "no_archivar_principal"
