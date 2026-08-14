from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PagoFijo(Base):
    """Tabla existente del bot, extendida (migración 003) para pagos recurrentes.

    Las columnas nuevas son aditivas con default — el bot las ignora sin romperse.
    """

    __tablename__ = "pagos_fijos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    dia_mes: Mapped[int] = mapped_column(Integer, nullable=False)
    categoria: Mapped[str | None] = mapped_column(Text, server_default=text("'Servicios'"))
    activo: Mapped[bool | None] = mapped_column(Boolean, server_default=text("true"))
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id"))
    # Nuevas (migración 003): 'mensual' | 'semanal' | 'anual'
    frecuencia: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'mensual'"))
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    auto_registrar: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    ultimo_registro: Mapped[date | None] = mapped_column(Date)  # idempotencia del job de auto-registro
