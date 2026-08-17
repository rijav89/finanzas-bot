from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, text
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
        "tipo": c.tipo,
        "icono": c.icono,
        "color": c.color,
        "es_sistema": c.es_sistema,
        "activa": c.activa,
    }


@router.get("")
async def listar(
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_lectura),
    tipo: Literal["gasto", "ingreso"] | None = Query(default=None),
    incluir_archivadas: bool = Query(default=False),
):
    """Categorías de sistema (compartidas con el bot) + las propias del usuario.

    La pantalla de Configuración necesita ver también las archivadas para poder
    reactivarlas; los selectores de captura, no.
    """
    filtros = [or_(Categoria.usuario_id.is_(None), Categoria.usuario_id == user.usuario_id)]
    if not incluir_archivadas:
        filtros.append(Categoria.activa.is_(True))
    if tipo is not None:
        # 'Transferencia' es tipo 'ambos': entra en las dos listas
        filtros.append(Categoria.tipo.in_((tipo, "ambos")))

    filas = (
        await db.scalars(
            select(Categoria).where(*filtros).order_by(Categoria.es_sistema.desc(), Categoria.nombre)
        )
    ).all()
    return ok([_serializar(c) for c in filas])


@router.post("", status_code=201)
async def crear(
    body: CategoriaCrear,
    user: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verificar_nombre_libre(db, user.usuario_id, body.nombre)
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
    cambios = body.model_dump(exclude_unset=True)

    nombre_nuevo = cambios.get("nombre")
    if nombre_nuevo and nombre_nuevo != cat.nombre:
        await _verificar_nombre_libre(db, user.usuario_id, nombre_nuevo, excluir=cat.id)
        await _arrastrar_movimientos(db, user.usuario_id, cat.nombre, nombre_nuevo)

    for campo, valor in cambios.items():
        setattr(cat, campo, valor)
    await db.flush()
    return ok(_serializar(cat))


async def _arrastrar_movimientos(
    db: AsyncSession, usuario_id: int, viejo: str, nuevo: str
) -> None:
    """`transacciones.categoria` e `ingresos.categoria` son TEXT sin FK (el bot escribe
    strings), así que renombrar el catálogo sin tocarlos dejaría los movimientos
    apuntando a una categoría que ya no existe."""
    params = {"uid": usuario_id, "viejo": viejo, "nuevo": nuevo}
    for tabla in ("transacciones", "ingresos"):
        await db.execute(
            text(
                f"UPDATE {tabla} SET categoria = :nuevo "  # noqa: S608 — tabla es literal
                "WHERE usuario_id = :uid AND categoria = :viejo"
            ),
            params,
        )


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


async def _verificar_nombre_libre(
    db: AsyncSession, usuario_id: int, nombre: str, excluir: int | None = None
) -> None:
    """El nombre no puede chocar ni con una de sistema ni con otra propia."""
    condiciones = [
        or_(Categoria.usuario_id.is_(None), Categoria.usuario_id == usuario_id),
        func.lower(Categoria.nombre) == nombre.lower(),
    ]
    if excluir is not None:
        condiciones.append(Categoria.id != excluir)
    if await db.scalar(select(Categoria.id).where(*condiciones)) is not None:
        raise HTTPException(status_code=409, detail="nombre_duplicado")


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
