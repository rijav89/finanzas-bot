from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

# Las 14 categorías del bot (bot/categorias.py) + 'Transferencia' (reservada interna).
# Se siembran como filas de sistema (usuario_id NULL, es_sistema=true) en la migración 003.
CATEGORIAS_SISTEMA = [
    "Comida", "Supermercado", "Transporte", "Servicios", "Salud",
    "Educacion", "Ropa", "Entretenimiento", "Tecnologia", "Finanzas",
    "Mascotas", "Belleza", "Hogar", "Otros",
]
CATEGORIA_TRANSFERENCIA = "Transferencia"


class Categoria(Base):
    """Catálogo de categorías: filas de sistema (usuario_id NULL) + filas por usuario.

    transacciones.categoria e ingresos.categoria siguen siendo TEXT sin FK
    (el bot escribe strings hardcoded); el panel valida contra esta tabla.
    """

    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    # 'gasto' | 'ingreso' | 'ambos' (Transferencia, que aparece en los dos lados)
    tipo: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'gasto'"))
    icono: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(Text)
    es_sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (UniqueConstraint("usuario_id", "nombre", name="uq_categoria_usuario_nombre"),)
