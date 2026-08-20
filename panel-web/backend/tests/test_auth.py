import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_codigo
from app.models import CodigoVinculacion
from app.services.gotrue import get_gotrue
from tests.conftest import AUTH_UID_A, AUTH_UID_SIN_VINCULO, como, token_para
from app.main import app

pytestmark = pytest.mark.asyncio


class GoTrueFake:
    async def login(self, email, password):
        if password != "correcta":
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="credenciales_invalidas")
        return {
            "access_token": token_para(AUTH_UID_A, email),
            "refresh_token": "refresh-fake-1",
        }

    async def refresh(self, refresh_token):
        return {
            "access_token": token_para(AUTH_UID_A),
            "refresh_token": "refresh-fake-2",
        }

    async def logout(self, access_token):
        pass


async def test_login_setea_cookies_y_me_funciona(cliente, datos):
    app.dependency_overrides[get_gotrue] = lambda: GoTrueFake()

    r = await cliente.post(
        "/api/v1/auth/login", json={"email": "a@test.com", "password": "correcta"}
    )
    assert r.status_code == 200
    assert r.json()["error"] is None
    assert "sb_access" in r.cookies

    r = await cliente.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["data"]["vinculado"] is True


async def test_login_credenciales_malas(cliente, datos):
    app.dependency_overrides[get_gotrue] = lambda: GoTrueFake()
    r = await cliente.post(
        "/api/v1/auth/login", json={"email": "a@test.com", "password": "incorrecta"}
    )
    assert r.status_code == 401
    assert r.json()["error"] == "credenciales_invalidas"


async def test_endpoint_protegido_sin_cookie_401(cliente, datos):
    r = await cliente.get("/api/v1/cuentas")
    assert r.status_code == 401


async def test_usuario_sin_vinculo_recibe_409(cliente, datos):
    como(cliente, AUTH_UID_SIN_VINCULO)
    r = await cliente.get("/api/v1/cuentas")
    assert r.status_code == 409
    assert r.json()["error"] == "vinculo_requerido"


async def test_mutacion_sin_header_csrf_403(cliente, datos):
    como(cliente, AUTH_UID_A)
    r = await cliente.post(
        "/api/v1/cuentas",
        json={"nombre": "Nueva"},
        headers={"X-Requested-With": ""},
    )
    assert r.status_code == 403


async def test_vincular_con_codigo_valido(cliente, sesiones, datos):
    async with sesiones() as s:
        async with s.begin():
            s.add(
                CodigoVinculacion(
                    usuario_id=datos["usuario_a"],
                    codigo_hash=hash_codigo("ABCD2345"),
                    expira_en=datetime.now(timezone.utc) + timedelta(minutes=10),
                )
            )
    # Usuario A "des-vinculado" no existe: usamos un auth_uid nuevo contra el
    # mismo usuario — debe fallar porque el telegram ya está vinculado
    como(cliente, AUTH_UID_SIN_VINCULO)
    r = await cliente.post("/api/v1/auth/vincular", json={"codigo": "ABCD2345"})
    assert r.status_code == 409
    assert r.json()["error"] == "telegram_ya_vinculado"


async def test_vincular_codigo_invalido(cliente, datos):
    como(cliente, AUTH_UID_SIN_VINCULO)
    r = await cliente.post("/api/v1/auth/vincular", json={"codigo": "NOEXISTE"})
    assert r.status_code == 400


async def test_vincular_flujo_completo_usuario_nuevo(cliente, sesiones):
    """Usuario de Telegram sin vincular + web nueva → vínculo exitoso."""
    from app.models import Usuario

    async with sesiones() as s:
        async with s.begin():
            u = Usuario(telegram_id=333)
            s.add(u)
            await s.flush()
            s.add(
                CodigoVinculacion(
                    usuario_id=u.id,
                    codigo_hash=hash_codigo("XYZW6789"),
                    expira_en=datetime.now(timezone.utc) + timedelta(minutes=10),
                )
            )
            uid = u.id

    como(cliente, AUTH_UID_SIN_VINCULO)
    r = await cliente.post("/api/v1/auth/vincular", json={"codigo": "xyzw6789"})
    assert r.status_code == 200
    assert r.json()["data"]["usuario_id"] == uid

    # Reutilizar el código debe fallar (un solo uso)
    otro_uid = str(uuid.uuid4())
    como(cliente, otro_uid)
    r = await cliente.post("/api/v1/auth/vincular", json={"codigo": "XYZW6789"})
    assert r.status_code == 400


# ── Alta de usuarios nuevos con el código del bot ────────────────────────────

AUTH_UID_NUEVO = "9f1c2d3e-4b5a-6c7d-8e9f-0a1b2c3d4e5f"


class GoTrueAlta(GoTrueFake):
    """Registra la cuenta creada, para poder afirmar que NO se creó cuando el
    código era inválido."""

    def __init__(self):
        self.altas: list[str] = []

    async def signup(self, email, password):
        self.altas.append(email)
        return {
            "user": {"id": AUTH_UID_NUEVO, "email": email},
            "access_token": token_para(AUTH_UID_NUEVO, email),
            "refresh_token": "refresh-alta",
        }


async def _codigo_para(sesiones, usuario_id: int, codigo: str, minutos: int = 10):
    async with sesiones() as s:
        async with s.begin():
            s.add(
                CodigoVinculacion(
                    usuario_id=usuario_id,
                    codigo_hash=hash_codigo(codigo),
                    expira_en=datetime.now(timezone.utc) + timedelta(minutes=minutos),
                )
            )


async def test_registro_crea_cuenta_vincula_y_deja_sesion(cliente, sesiones, datos):
    """Un usuario de Telegram sin cuenta web entra en un solo paso."""
    from app.models import Usuario

    async with sesiones() as s:
        async with s.begin():
            nuevo = Usuario(telegram_id=777001)
            s.add(nuevo)
            await s.flush()
            uid = nuevo.id
    await _codigo_para(sesiones, uid, "NUEVO123")

    falso = GoTrueAlta()
    app.dependency_overrides[get_gotrue] = lambda: falso

    r = await cliente.post(
        "/api/v1/auth/registrar",
        json={"email": "nuevo@test.com", "password": "unaClaveLarga1", "codigo": "NUEVO123"},
    )
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["vinculado"] is True
    assert d["usuario_id"] == uid
    assert d["sesion_iniciada"] is True
    assert "sb_access" in r.cookies

    # Queda operativo sin volver a iniciar sesión
    r = await cliente.get("/api/v1/auth/me")
    assert r.json()["data"]["usuario_id"] == uid


async def test_codigo_malo_no_crea_cuenta_en_supabase(cliente, sesiones, datos):
    """Lo importante no es el error, es que no quede una cuenta huérfana en Auth."""
    falso = GoTrueAlta()
    app.dependency_overrides[get_gotrue] = lambda: falso

    r = await cliente.post(
        "/api/v1/auth/registrar",
        json={"email": "colado@test.com", "password": "unaClaveLarga1", "codigo": "NOEXISTE"},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "codigo_invalido_o_expirado"
    assert falso.altas == []


async def test_codigo_vencido_no_crea_cuenta(cliente, sesiones, datos):
    await _codigo_para(sesiones, datos["usuario_b"], "VIEJO123", minutos=-1)

    falso = GoTrueAlta()
    app.dependency_overrides[get_gotrue] = lambda: falso

    r = await cliente.post(
        "/api/v1/auth/registrar",
        json={"email": "tarde@test.com", "password": "unaClaveLarga1", "codigo": "VIEJO123"},
    )
    assert r.status_code == 400
    assert falso.altas == []


async def test_no_registrarse_con_un_telegram_ya_vinculado(cliente, sesiones, datos):
    """usuario_a ya tiene su cuenta web: su código no sirve para abrir otra."""
    await _codigo_para(sesiones, datos["usuario_a"], "TOMADO12")

    falso = GoTrueAlta()
    app.dependency_overrides[get_gotrue] = lambda: falso

    r = await cliente.post(
        "/api/v1/auth/registrar",
        json={"email": "otro@test.com", "password": "unaClaveLarga1", "codigo": "TOMADO12"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "telegram_ya_vinculado"
    assert falso.altas == []


async def test_el_codigo_no_se_puede_reusar(cliente, sesiones, datos):
    from app.models import Usuario

    async with sesiones() as s:
        async with s.begin():
            nuevo = Usuario(telegram_id=777002)
            s.add(nuevo)
            await s.flush()
            uid = nuevo.id
    await _codigo_para(sesiones, uid, "UNAVEZ12")

    app.dependency_overrides[get_gotrue] = lambda: GoTrueAlta()
    cuerpo = {"email": "uno@test.com", "password": "unaClaveLarga1", "codigo": "UNAVEZ12"}
    assert (await cliente.post("/api/v1/auth/registrar", json=cuerpo)).status_code == 201

    cliente.cookies.clear()
    r = await cliente.post(
        "/api/v1/auth/registrar",
        json={**cuerpo, "email": "dos@test.com"},
    )
    assert r.status_code == 400


async def test_contrasena_corta_rechazada(cliente, datos):
    app.dependency_overrides[get_gotrue] = lambda: GoTrueAlta()
    r = await cliente.post(
        "/api/v1/auth/registrar",
        json={"email": "x@test.com", "password": "corta", "codigo": "ABCD1234"},
    )
    assert r.status_code == 422
