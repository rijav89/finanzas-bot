from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, require_csrf
from app.models import Cuenta
from app.schemas.common import ok
from app.schemas.cuentas import CuentaCrear, CuentaEditar, CuentaOut
from app.services.movimientos import cuenta_propia

router = APIRouter(prefix="/cuentas", tags=["cuentas"], dependencies=[Depends(require_csrf)])


@router.get("")
async def listar(
    user: UsuarioActual = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    filas = (
        await db.scalars(
            select(Cuenta)
            .where(Cuenta.usuario_id == user.usuario_id, Cuenta.activa.is_(True))
            .order_by(Cuenta.es_principal.desc(), Cuenta.nombre)
        )
    ).all()
    return ok([CuentaOut.model_validate(c).model_dump() for c in filas])


@router.post("", status_code=201)
async def crear(
    body: CuentaCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    duplicada = await db.scalar(
        select(Cuenta.id).where(
            Cuenta.usuario_id == user.usuario_id,
            func.lower(Cuenta.nombre) == body.nombre.lower(),
            Cuenta.activa.is_(True),
        )
    )
    if duplicada is not None:
        raise HTTPException(status_code=409, detail="nombre_duplicado")

    cuenta = Cuenta(
        usuario_id=user.usuario_id,
        nombre=body.nombre,
        tipo=body.tipo,
        saldo_inicial=body.saldo_inicial,
        es_principal=body.es_principal,
    )
    if body.es_principal:
        await _quitar_principal_actual(db, user.usuario_id)
    db.add(cuenta)
    await db.flush()
    return ok(CuentaOut.model_validate(cuenta).model_dump())


@router.patch("/{cuenta_id}")
async def editar(
    cuenta_id: int,
    body: CuentaEditar,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cuenta = await cuenta_propia(db, user.usuario_id, cuenta_id)
    cambios = body.model_dump(exclude_unset=True)
    if cambios.get("es_principal"):
        await _quitar_principal_actual(db, user.usuario_id)
    for campo, valor in cambios.items():
        setattr(cuenta, campo, valor)
    await db.flush()
    return ok(CuentaOut.model_validate(cuenta).model_dump())


@router.delete("/{cuenta_id}")
async def archivar(
    cuenta_id: int,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cuenta = await cuenta_propia(db, user.usuario_id, cuenta_id)
    if cuenta.es_principal:
        raise HTTPException(status_code=400, detail="no_archivar_principal")
    cuenta.activa = False
    return ok({"archivada": True})


async def _quitar_principal_actual(db: AsyncSession, usuario_id: int) -> None:
    actual = await db.scalar(
        select(Cuenta).where(
            Cuenta.usuario_id == usuario_id,
            Cuenta.es_principal.is_(True),
            Cuenta.activa.is_(True),
        )
    )
    if actual is not None:
        actual.es_principal = False
