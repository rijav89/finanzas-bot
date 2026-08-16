import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    get_auth_claims,
    get_db_basico,
    get_db_lectura_libre,
    require_csrf,
)
from app.core.security import (
    COOKIE_ACCESS,
    COOKIE_REFRESH,
    clear_auth_cookies,
    decode_supabase_jwt,
    set_auth_cookies,
    vinculo_cache_set,
)
from app.models import VinculoAuth
from app.schemas.auth import LoginIn, VincularIn
from app.schemas.common import ok
from app.services.gotrue import GoTrueClient, get_gotrue
from app.services.vinculacion import canjear_codigo

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(require_csrf)])


@router.post("/login")
async def login(
    body: LoginIn, response: Response, gotrue: GoTrueClient = Depends(get_gotrue)
):
    sesion = await gotrue.login(body.email, body.password)
    set_auth_cookies(response, sesion["access_token"], sesion["refresh_token"])
    claims = decode_supabase_jwt(sesion["access_token"])
    return ok({"email": claims.get("email"), "auth_uid": claims.get("sub")})


@router.post("/refresh")
async def refresh(
    request: Request, response: Response, gotrue: GoTrueClient = Depends(get_gotrue)
):
    token = request.cookies.get(COOKIE_REFRESH)
    if not token:
        raise HTTPException(status_code=401, detail="sin_refresh_token")
    sesion = await gotrue.refresh(token)
    set_auth_cookies(response, sesion["access_token"], sesion["refresh_token"])
    return ok({"renovado": True})


@router.post("/logout")
async def logout(
    request: Request, response: Response, gotrue: GoTrueClient = Depends(get_gotrue)
):
    access = request.cookies.get(COOKIE_ACCESS)
    if access:
        await gotrue.logout(access)
    clear_auth_cookies(response)
    return ok({"sesion_cerrada": True})


@router.post("/vincular")
async def vincular(
    body: VincularIn,
    claims: dict = Depends(get_auth_claims),
    db: AsyncSession = Depends(get_db_basico),
):
    usuario_id = await canjear_codigo(db, claims["sub"], body.codigo)
    vinculo_cache_set(claims["sub"], usuario_id)
    return ok({"vinculado": True, "usuario_id": usuario_id})


@router.get("/me")
async def me(
    claims: dict = Depends(get_auth_claims), db: AsyncSession = Depends(get_db_lectura_libre)
):
    usuario_id = await db.scalar(
        select(VinculoAuth.usuario_id).where(
            VinculoAuth.auth_uid == uuid.UUID(claims["sub"])
        )
    )
    return ok(
        {
            "email": claims.get("email"),
            "auth_uid": claims["sub"],
            "vinculado": usuario_id is not None,
            "usuario_id": usuario_id,
        }
    )
