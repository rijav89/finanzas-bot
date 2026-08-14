from datetime import datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Transaccion(Base):
    """Tabla existente del bot — SOLO gastos (semántica heredada).

    Las transferencias se modelan como par gasto+ingreso con categoria='Transferencia'
    y se excluyen de los totales (AND categoria != 'Transferencia').
    """

    __tablename__ = "transacciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    monto: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    medio: Mapped[str | None] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str | None] = mapped_column(Text)  # TEXT sin FK a propósito (el bot escribe strings)
    destinatario: Mapped[str | None] = mapped_column(Text, server_default=text("'No detectado'"))
    fecha_voucher: Mapped[str | None] = mapped_column(Text, server_default=text("'No detectada'"))  # crudo OCR
    fecha: Mapped[datetime | None] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id"))


class Ingreso(Base):
    """Tabla existente del bot."""

    __tablename__ = "ingresos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    monto: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str | None] = mapped_column(Text, server_default=text("'Ingreso'"))
    fecha: Mapped[datetime | None] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id"))
