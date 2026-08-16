"""Fixtures: SQLite async como BD de prueba, JWTs firmados con secret de test,
GoTrue mockeado. El enforcement anti-IDOR es app-level, así que se prueba igual
que en Postgres (RLS es defensa en profundidad y se verifica en F6 contra la BD real).
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

# Config de entorno ANTES de importar la app (Settings/engine se crean al importar)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("SUPABASE_JWT_SECRET", "secreto-de-test-nada-productivo")
os.environ.setdefault("COOKIE_SECURE", "false")

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.core.deps as deps_mod
from app.core.security import hash_codigo, vinculo_cache_clear
from app.main import app
from app.models import Base, Cuenta, CodigoVinculacion, Usuario, VinculoAuth

SECRET = os.environ["SUPABASE_JWT_SECRET"]

AUTH_UID_A = str(uuid.uuid4())
AUTH_UID_B = str(uuid.uuid4())
AUTH_UID_SIN_VINCULO = str(uuid.uuid4())


def token_para(auth_uid: str, email: str = "test@test.com") -> str:
    ahora = datetime.now(timezone.utc)
    return pyjwt.encode(
        {
            "sub": auth_uid,
            "email": email,
            "aud": "authenticated",
            "iat": ahora,
            "exp": ahora + timedelta(minutes=15),
        },
        SECRET,
        algorithm="HS256",
    )


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def sesiones(db_engine, monkeypatch):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    # En producción la de lectura va en AUTOCOMMIT sobre el mismo pool; en SQLite
    # basta con la misma factory (lo que se prueba es la lógica, no el aislamiento).
    monkeypatch.setattr(deps_mod, "async_session", factory)
    monkeypatch.setattr(deps_mod, "async_session_lectura", factory)
    vinculo_cache_clear()
    return factory


@pytest_asyncio.fixture
async def datos(sesiones):
    """Dos usuarios vinculados (A y B), cada uno con una cuenta; devuelve ids."""
    async with sesiones() as s:
        async with s.begin():
            ua = Usuario(telegram_id=111)
            ub = Usuario(telegram_id=222)
            s.add_all([ua, ub])
            await s.flush()
            s.add_all(
                [
                    VinculoAuth(usuario_id=ua.id, auth_uid=uuid.UUID(AUTH_UID_A)),
                    VinculoAuth(usuario_id=ub.id, auth_uid=uuid.UUID(AUTH_UID_B)),
                ]
            )
            ca = Cuenta(usuario_id=ua.id, nombre="Principal", es_principal=True, activa=True)
            cb = Cuenta(usuario_id=ub.id, nombre="Principal", es_principal=True, activa=True)
            ca2 = Cuenta(usuario_id=ua.id, nombre="Ahorro", tipo="ahorro", activa=True)
            s.add_all([ca, cb, ca2])
            await s.flush()
            ids = {
                "usuario_a": ua.id,
                "usuario_b": ub.id,
                "cuenta_a": ca.id,
                "cuenta_b": cb.id,
                "cuenta_a2": ca2.id,
            }
    return ids


@pytest_asyncio.fixture
async def cliente(sesiones):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Requested-With": "fetch"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


def como(cliente: AsyncClient, auth_uid: str) -> None:
    cliente.cookies.set("sb_access", token_para(auth_uid))
