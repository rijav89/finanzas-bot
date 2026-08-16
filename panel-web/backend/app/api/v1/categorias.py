from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioActual, get_current_user, get_db, get_db_lectura, require_csrf
from app.models import Categoria
from app.schemas.common import ok
from app.schemas.modulos import CategoriaCrear, CategoriaEditar

router = APIRouter(prefix="/categorias", tags=["categorias"], dependencies=[Depends(require_csrf)])


def _serializar(c: Categoria) -> dict:
    return {
        "id": c.id,
        "nombre": c.nombre,
        "icono": c.icono,
        "color": c.color,
        "es_sistema": c.es_sistema,
        "activa": c.activa,
    }


@router.get("")
async def listar(
    user: UsuarioActual = Depends(get_current_user), db: AsyncSession = Depends(get_db_lectura)
):
    """Categorías de sistema (compartidas con el bot) + las propias del usuario."""
    filas = (
        await db.scalars(
            select(Categoria)
            .where(
                or_(Categoria.usuario_id.is_(None), Categoria.usuario_id == user.usuario_id),
                Categoria.activa.is_(True),
            )
            .order_by(Categoria.es_sistema.desc(), Categoria.nombre)
        )
    ).all()
    return ok([_serializar(c) for c in filas])


@router.post("", status_code=201)
async def crear(
    body: CategoriaCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # El nombre no puede chocar ni con una de sistema ni con otra propia
    choque = await db.scalar(
        select(Categoria.id).where(
            or_(Categoria.usuario_id.is_(None), Categoria.usuario_id == user.usuario_id),
            func.lower(Categoria.nombre) == body.nombre.lower(),
        )
    )
    if choque is not None:
        raise HTTPException(status_code=409, detail="nombre_duplicado")

    cat = Categoria(usuario_id=user.usuario_id, **body.model_dump())
    db.add(cat)
    await db.flush()
    return ok(_serializar(cat))


@router.patch("/{categoria_id}")
async def editar(
    categoria_id: int,
    body: CategoriaEditar,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cat = await _propia(db, user.usuario_id, categoria_id)
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(cat, campo, valor)
    await db.flush()
    return ok(_serializar(cat))


@router.delete("/{categoria_id}")
async def archivar(
    categoria_id: int,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: los movimientos ya registrados conservan el nombre como texto."""
    cat = await _propia(db, user.usuario_id, categoria_id)
    cat.activa = False
    return ok({"archivada": True})


async def _propia(db: AsyncSession, usuario_id: int, categoria_id: int) -> Categoria:
    """Solo categorías del usuario: las de sistema son de solo lectura."""
    cat = await db.scalar(
        select(Categoria).where(
            Categoria.id == categoria_id, Categoria.usuario_id == usuario_id
        )
    )
    if cat is None:
        raise HTTPException(status_code=404, detail="categoria_no_encontrada")
    return cat
