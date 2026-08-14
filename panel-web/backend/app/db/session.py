from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# Pool pequeño a propósito: servidor de 1GB RAM compartido con nginx,
# y el pooler de Supabase free tiene límite de conexiones.
engine = create_async_engine(
    get_settings().database_url,
    pool_size=3,
    max_overflow=2,
    pool_pre_ping=True,  # Supabase free pausa proyectos; detectar conexiones muertas
    # Defensivo: si el pooler pasara a transaction-mode (puerto 6543), los
    # prepared statements cacheados de asyncpg romperían. Con session-mode (5432) es inocuo.
    connect_args={"statement_cache_size": 0},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
