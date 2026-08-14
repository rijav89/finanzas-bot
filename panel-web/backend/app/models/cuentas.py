from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Cuenta(Base):
    """Tabla existente del bot. La columna `tipo` es nueva (migración 003, aditiva)."""

    __tablename__ = "cuentas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    saldo_inicial: Mapped[Decimal | None] = mapped_column(Numeric, server_default=text("0"))
    es_principal: Mapped[bool | None] = mapped_column(Boolean, server_default=text("false"))
    activa: Mapped[bool | None] = mapped_column(Boolean, server_default=text("true"))
    # 'corriente' | 'ahorro' — el bot la ignora (default preserva su comportamiento)
    tipo: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'corriente'"))


class MetaAhorro(Base):
    """Meta de ahorro 1:1 con una cuenta de tipo 'ahorro'."""

    __tablename__ = "metas_ahorro"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(
        ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    monto_objetivo: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_objetivo: Mapped[date | None] = mapped_column(Date)

    __table_args__ = (CheckConstraint("monto_objetivo > 0", name="ck_meta_ahorro_monto_pos"),)
