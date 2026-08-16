from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.v1 import (
    ahorros,
    auth,
    categorias,
    cuentas,
    dashboard,
    deudas,
    movimientos,
    perfil,
    presupuestos,
    recurrentes,
)
from app.db.session import engine
from app.schemas.common import err


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

for _router in (
    auth.router,
    cuentas.router,
    movimientos.router,
    dashboard.router,
    categorias.router,
    presupuestos.router,
    deudas.router,
    ahorros.router,
    recurrentes.router,
    perfil.router,
):
    app.include_router(_router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    respuesta = JSONResponse(status_code=exc.status_code, content=err(str(exc.detail)))
    # Propagar Set-Cookie u otros headers que el endpoint haya adjuntado
    if exc.headers:
        for k, v in exc.headers.items():
            respuesta.headers[k] = v
    return respuesta


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=err("payload_invalido"))


@app.exception_handler(OperationalError)
async def db_exc_handler(request: Request, exc: OperationalError):
    # Supabase free pausa proyectos inactivos: 503 explícito en vez de 500 opaco
    return JSONResponse(status_code=503, content=err("db_unavailable"))


@app.get("/api/v1/health")
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content=err("db_unavailable"))
    return {"data": {"db": "ok", "version": app.version}, "error": None}
