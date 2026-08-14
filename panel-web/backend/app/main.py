from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="FinanzasBot Panel API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.get("/api/v1/health")
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        # Supabase free pausa proyectos inactivos; responder 503 explícito en vez de colgarse
        return JSONResponse(status_code=503, content={"data": None, "error": "db_unavailable"})
    return {"data": {"db": "ok", "version": app.version}, "error": None}
