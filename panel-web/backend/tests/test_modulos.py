"""Módulos de F4: categorías, presupuestos, deudas, ahorros, recurrentes, perfil/metas.
Incluye los casos anti-IDOR de cada recurso nuevo."""
import pytest

from tests.conftest import AUTH_UID_A, AUTH_UID_B, como

pytestmark = pytest.mark.asyncio


# ── Categorías ───────────────────────────────────────────────────────────────

async def test_crear_categoria_propia_y_listar(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post("/api/v1/categorias", json={"nombre": "Gimnasio", "color": "#2a78d6"})
    assert r.status_code == 201

    r = await cliente.get("/api/v1/categorias")
    nombres = {c["nombre"] for c in r.json()["data"]}
    assert "Gimnasio" in nombres


async def test_categoria_duplicada_409(cliente, datos, sesiones):
    from app.models import Categoria

    async with sesiones() as s:
        async with s.begin():
            s.add(Categoria(usuario_id=None, nombre="Comida", es_sistema=True))

    como(cliente, AUTH_UID_A)
    r = await cliente.post("/api/v1/categorias", json={"nombre": "comida"})
    assert r.status_code == 409


async def test_no_editar_categoria_ajena(cliente, datos):
    como(cliente, AUTH_UID_B)
    r = await cliente.post("/api/v1/categorias", json={"nombre": "SoloDeB"})
    cat_b = r.json()["data"]["id"]

    como(cliente, AUTH_UID_A)
    r = await cliente.patch(f"/api/v1/categorias/{cat_b}", json={"nombre": "Robada"})
    assert r.status_code == 404


async def test_filtrar_categorias_por_tipo(cliente, datos, sesiones):
    from app.models import Categoria

    async with sesiones() as s:
        async with s.begin():
            s.add_all(
                [
                    Categoria(usuario_id=None, nombre="Comida", es_sistema=True, tipo="gasto"),
                    Categoria(usuario_id=None, nombre="Sueldo", es_sistema=True, tipo="ingreso"),
                    Categoria(
                        usuario_id=None, nombre="Transferencia", es_sistema=True, tipo="ambos"
                    ),
                ]
            )

    como(cliente, AUTH_UID_A)
    r = await cliente.get("/api/v1/categorias", params={"tipo": "ingreso"})
    nombres = {c["nombre"] for c in r.json()["data"]}
    assert "Sueldo" in nombres
    assert "Comida" not in nombres
    # 'ambos' cae de los dos lados: un traslado aparece como salida y como entrada
    assert "Transferencia" in nombres


async def test_renombrar_categoria_arrastra_los_movimientos(cliente, datos, sesiones):
    """La columna `categoria` es TEXT sin FK: si el rename no arrastra, los
    movimientos quedan apuntando a una categoría que ya no existe."""
    from sqlalchemy import text

    como(cliente, AUTH_UID_A)
    r = await cliente.post("/api/v1/categorias", json={"nombre": "Gimnasio"})
    cat_id = r.json()["data"]["id"]

    r = await cliente.post(
        "/api/v1/gastos",
        json={"monto": "50.00", "categoria": "Gimnasio", "cuenta_id": datos["cuenta_a"]},
    )
    assert r.status_code == 201

    r = await cliente.patch(f"/api/v1/categorias/{cat_id}", json={"nombre": "Deporte"})
    assert r.status_code == 200

    async with sesiones() as s:
        categorias = (
            await s.execute(
                text("SELECT categoria FROM transacciones WHERE usuario_id = :uid"),
                {"uid": datos["usuario_a"]},
            )
        ).scalars().all()
    assert categorias == ["Deporte"]


async def test_renombrar_a_nombre_existente_409(cliente, datos, sesiones):
    from app.models import Categoria

    async with sesiones() as s:
        async with s.begin():
            s.add(Categoria(usuario_id=None, nombre="Salud", es_sistema=True))

    como(cliente, AUTH_UID_A)
    cat_id = (await cliente.post("/api/v1/categorias", json={"nombre": "Gimnasio"})).json()["data"]["id"]
    r = await cliente.patch(f"/api/v1/categorias/{cat_id}", json={"nombre": "salud"})
    assert r.status_code == 409


# ── Presupuestos ─────────────────────────────────────────────────────────────

async def test_presupuesto_semaforo_y_gastado(cliente, datos):
    como(cliente, AUTH_UID_A)
    await cliente.put(
        "/api/v1/presupuestos",
        json={
            "anio": 2026,
            "mes": 8,
            "items": [
                {"categoria": "Comida", "monto_limite": "100"},
                {"categoria": "Transporte", "monto_limite": "200"},
            ],
        },
    )
    # Gasto que supera el límite de Comida
    await cliente.post(
        "/api/v1/gastos",
        json={
            "monto": "120",
            "categoria": "Comida",
            "cuenta_id": datos["cuenta_a"],
            "fecha": "2026-08-10",
        },
    )

    r = await cliente.get("/api/v1/presupuestos?anio=2026&mes=8")
    items = {i["categoria"]: i for i in r.json()["data"]["items"]}
    assert items["Comida"]["gastado"] == 120
    assert items["Comida"]["semaforo"] == "critico"
    assert items["Transporte"]["semaforo"] == "bien"


async def test_presupuesto_upsert_reemplaza_periodo(cliente, datos):
    como(cliente, AUTH_UID_A)
    await cliente.put(
        "/api/v1/presupuestos",
        json={"anio": 2026, "mes": 9, "items": [{"categoria": "Comida", "monto_limite": "100"}]},
    )
    await cliente.put(
        "/api/v1/presupuestos",
        json={"anio": 2026, "mes": 9, "items": [{"categoria": "Salud", "monto_limite": "50"}]},
    )
    r = await cliente.get("/api/v1/presupuestos?anio=2026&mes=9")
    cats = [i["categoria"] for i in r.json()["data"]["items"]]
    assert cats == ["Salud"]


# ── Deudas ───────────────────────────────────────────────────────────────────

async def test_deuda_genera_cronograma_que_suma_el_total(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/deudas",
        json={
            "tipo": "prestamo_recibido",
            "acreedor": "Banco",
            "monto_total": "1000",
            "num_cuotas": 3,
            "fecha_inicio": "2026-08-15",
            "cuenta_id": datos["cuenta_a"],
        },
    )
    assert r.status_code == 201
    deuda_id = r.json()["data"]["id"]

    r = await cliente.get(f"/api/v1/deudas/{deuda_id}")
    cuotas = r.json()["data"]["cuotas"]
    assert len(cuotas) == 3
    # El redondeo se ajusta en la última cuota: deben sumar exactamente el total
    assert round(sum(c["monto"] for c in cuotas), 2) == 1000.0


async def test_pagar_cuota_crea_gasto_y_cierra_deuda(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/deudas",
        json={
            "tipo": "prestamo_recibido",
            "acreedor": "Juan",
            "monto_total": "200",
            "num_cuotas": 2,
            "fecha_inicio": "2026-08-01",
            "cuenta_id": datos["cuenta_a"],
        },
    )
    deuda_id = r.json()["data"]["id"]

    r = await cliente.post(f"/api/v1/deudas/{deuda_id}/cuotas/1/pagar", json={})
    assert r.status_code == 200
    assert r.json()["data"]["transaccion_id"] is not None
    assert r.json()["data"]["deuda"]["estado"] == "activa"

    # La cuota pagada aparece como gasto real
    r = await cliente.get("/api/v1/movimientos")
    descripciones = [m["descripcion"] for m in r.json()["data"]["items"]]
    assert any(d and "Cuota 1/2" in d for d in descripciones)

    # Pagar la última cierra la deuda
    r = await cliente.post(f"/api/v1/deudas/{deuda_id}/cuotas/2/pagar", json={})
    assert r.json()["data"]["deuda"]["estado"] == "pagada"

    # Repetir el pago falla
    r = await cliente.post(f"/api/v1/deudas/{deuda_id}/cuotas/2/pagar", json={})
    assert r.status_code == 409


async def test_no_ver_deuda_ajena(cliente, datos):
    como(cliente, AUTH_UID_B)
    r = await cliente.post(
        "/api/v1/deudas",
        json={
            "tipo": "tarjeta",
            "acreedor": "Visa B",
            "monto_total": "500",
            "fecha_inicio": "2026-08-01",
            "num_cuotas": 1,
            "cuenta_id": datos["cuenta_b"],
        },
    )
    deuda_b = r.json()["data"]["id"]

    como(cliente, AUTH_UID_A)
    assert (await cliente.get(f"/api/v1/deudas/{deuda_b}")).status_code == 404
    r = await cliente.post(f"/api/v1/deudas/{deuda_b}/cuotas/1/pagar", json={})
    assert r.status_code == 404


# ── Ahorros ──────────────────────────────────────────────────────────────────

async def test_meta_ahorro_calcula_progreso(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.put(
        f"/api/v1/ahorros/{datos['cuenta_a2']}/meta", json={"monto_objetivo": "1000"}
    )
    assert r.status_code == 200

    await cliente.post(
        "/api/v1/ingresos",
        json={"monto": "250", "cuenta_id": datos["cuenta_a2"], "descripcion": "ahorro"},
    )

    r = await cliente.get("/api/v1/ahorros")
    item = next(i for i in r.json()["data"]["items"] if i["cuenta_id"] == datos["cuenta_a2"])
    assert item["saldo"] == 250
    assert item["meta"]["porcentaje"] == 25.0
    assert item["meta"]["falta"] == 750
    assert item["meta"]["cumplida"] is False


async def test_no_definir_meta_en_cuenta_ajena(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.put(
        f"/api/v1/ahorros/{datos['cuenta_b']}/meta", json={"monto_objetivo": "100"}
    )
    assert r.status_code == 404


# ── Recurrentes ──────────────────────────────────────────────────────────────

async def test_recurrente_crear_y_proximo_vencimiento(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/recurrentes",
        json={
            "descripcion": "Netflix",
            "monto": "44.90",
            "dia_mes": 15,
            "categoria": "Entretenimiento",
            "cuenta_id": datos["cuenta_a"],
        },
    )
    assert r.status_code == 201
    assert r.json()["data"]["proximo_vencimiento"] is not None

    r = await cliente.get("/api/v1/recurrentes")
    assert r.json()["data"]["total_mensual"] == 44.90


async def test_recurrente_dia_31_no_revienta_en_meses_cortos(cliente, datos):
    """Día 31 debe caer al último día real del mes, no lanzar ValueError."""
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/recurrentes",
        json={"descripcion": "Alquiler", "monto": "900", "dia_mes": 31},
    )
    assert r.status_code == 201


async def test_no_editar_recurrente_ajeno(cliente, datos):
    como(cliente, AUTH_UID_B)
    r = await cliente.post(
        "/api/v1/recurrentes", json={"descripcion": "Luz B", "monto": "80", "dia_mes": 5}
    )
    pago_b = r.json()["data"]["id"]

    como(cliente, AUTH_UID_A)
    assert (
        await cliente.patch(f"/api/v1/recurrentes/{pago_b}", json={"monto": "1"})
    ).status_code == 404


# ── Perfil y metas ───────────────────────────────────────────────────────────

async def test_perfil_upsert(cliente, datos):
    como(cliente, AUTH_UID_A)
    assert (await cliente.get("/api/v1/perfil")).json()["data"] is None

    r = await cliente.put(
        "/api/v1/perfil",
        json={
            "ingreso_mensual_declarado": "3500",
            "moneda": "PEN",
            "perfil_riesgo": "moderado",
            "contexto_ia": {"nota": "freelance"},
        },
    )
    assert r.json()["data"]["perfil_riesgo"] == "moderado"

    r = await cliente.put(
        "/api/v1/perfil", json={"ingreso_mensual_declarado": "4000", "moneda": "PEN"}
    )
    assert r.json()["data"]["ingreso_mensual_declarado"] == 4000


async def test_metas_crud_y_aislamiento(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/metas", json={"titulo": "Viaje", "tipo": "ahorro", "monto_objetivo": "5000"}
    )
    assert r.status_code == 201
    meta_a = r.json()["data"]["id"]

    r = await cliente.patch(f"/api/v1/metas/{meta_a}", json={"cumplida": True})
    assert r.json()["data"]["cumplida"] is True

    como(cliente, AUTH_UID_B)
    assert (await cliente.get("/api/v1/metas")).json()["data"] == []
    assert (await cliente.delete(f"/api/v1/metas/{meta_a}")).status_code == 404


async def test_tipo_meta_invalido_422(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post("/api/v1/metas", json={"titulo": "X", "tipo": "inventado"})
    assert r.status_code == 422
