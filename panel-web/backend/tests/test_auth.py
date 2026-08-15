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
