from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_url = get_settings().database_url

# Supabase está a ~160 ms de este servidor, así que lo que domina el tiempo de
# respuesta es el NÚMERO de viajes de ida y vuelta, no el trabajo en la BD.
# Medido (2026-08-16): conexión nueva 2.5 s · pool_pre_ping +480 ms/req ·
# BEGIN+ROLLBACK implícito +270 ms/req · SET LOCAL +150 ms/req.
_kwargs: dict = {}
if _url.startswith("postgresql+asyncpg"):
    _kwargs.update(
        pool_size=5,
        max_overflow=2,
        # pool_pre_ping haría un roundtrip extra ANTES de cada query. En su lugar
        # reciclamos por tiempo y mantenemos el pool caliente con un keepalive.
        pool_pre_ping=False,
        pool_recycle=1500,  # 25 min: por debajo del corte de conexiones idle del pooler
        connect_args={
            # Defensivo si el pooler pasara a transaction-mode (puerto 6543)
            "statement_cache_size": 0,
            "server_settings": {"application_name": "panel-api"},
        },
    )

engine = create_async_engine(_url, **_kwargs)

# Mismo pool, sin transacción implícita: para lecturas (GET) ahorra BEGIN+ROLLBACK.
engine_lectura = engine.execution_options(isolation_level="AUTOCOMMIT")

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
async_session_lectura = async_sessionmaker(
    engine_lectura, class_=AsyncSession, expire_on_commit=False
)
