"""Casos anti-IDOR: el usuario A nunca puede leer/mutar recursos del usuario B (404)."""
import pytest

from tests.conftest import AUTH_UID_A, AUTH_UID_B, como

pytestmark = pytest.mark.asyncio


async def test_cuentas_solo_propias(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.get("/api/v1/cuentas")
    ids = {c["id"] for c in r.json()["data"]}
    assert datos["cuenta_a"] in ids
    assert datos["cuenta_b"] not in ids


async def test_no_editar_cuenta_ajena(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.patch(
        f"/api/v1/cuentas/{datos['cuenta_b']}", json={"nombre": "Hackeada"}
    )
    assert r.status_code == 404


async def test_no_archivar_cuenta_ajena(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.delete(f"/api/v1/cuentas/{datos['cuenta_b']}")
    assert r.status_code == 404


async def test_no_crear_gasto_en_cuenta_ajena(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/gastos",
        json={"monto": "10", "categoria": "Comida", "cuenta_id": datos["cuenta_b"]},
    )
    assert r.status_code == 404


async def test_no_editar_ni_borrar_gasto_ajeno(cliente, datos):
    como(cliente, AUTH_UID_B)
    r = await cliente.post(
        "/api/v1/gastos",
        json={"monto": "25", "categoria": "Comida", "cuenta_id": datos["cuenta_b"]},
    )
    gasto_b = r.json()["data"]["id"]

    como(cliente, AUTH_UID_A)
    r = await cliente.patch(f"/api/v1/gastos/{gasto_b}", json={"monto": "1"})
    assert r.status_code == 404
    r = await cliente.delete(f"/api/v1/gastos/{gasto_b}")
    assert r.status_code == 404


async def test_movimientos_no_mezcla_usuarios(cliente, datos):
    como(cliente, AUTH_UID_B)
    await cliente.post(
        "/api/v1/gastos",
        json={"monto": "99", "categoria": "Salud", "cuenta_id": datos["cuenta_b"]},
    )
    como(cliente, AUTH_UID_A)
    r = await cliente.get("/api/v1/movimientos")
    montos = [m["monto"] for m in r.json()["data"]["items"]]
    assert 99 not in [float(m) for m in montos]


async def test_no_transferir_hacia_cuenta_ajena(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/transferencias",
        json={
            "origen_id": datos["cuenta_a"],
            "destino_id": datos["cuenta_b"],
            "monto": "50",
        },
    )
    assert r.status_code == 404
