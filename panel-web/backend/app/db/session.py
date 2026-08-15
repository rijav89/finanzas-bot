from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_url = get_settings().database_url

# Pool pequeño a propósito: servidor de 1GB RAM compartido con nginx,
# y el pooler de Supabase free tiene límite de conexiones.
# statement_cache_size=0 es defensivo para asyncpg tras un pooler
# (inocuo en session-mode, necesario en transaction-mode).
# En SQLite (tests) esos kwargs no aplican (StaticPool).
_kwargs: dict = {"pool_pre_ping": True}
if _url.startswith("postgresql+asyncpg"):
    _kwargs.update(
        pool_size=3,
        max_overflow=2,
        connect_args={"statement_cache_size": 0},
    )

engine = create_async_engine(_url, **_kwargs)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
