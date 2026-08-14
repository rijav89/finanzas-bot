from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric, Text,
    UniqueConstraint, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Deuda(Base):
    __tablename__ = "deudas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 'prestamo_recibido' | 'prestamo_otorgado' | 'tarjeta'
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    acreedor: Mapped[str] = mapped_column(Text, nullable=False)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tasa_interes: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))  # TEA %
    num_cuotas: Mapped[int | None] = mapped_column(Integer)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    # 'activa' | 'pagada' | 'cancelada'
    estado: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'activa'"))
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id"))

    __table_args__ = (
        CheckConstraint("monto_total > 0", name="ck_deuda_monto_pos"),
        CheckConstraint(
            "tipo IN ('prestamo_recibido', 'prestamo_otorgado', 'tarjeta')",
            name="ck_deuda_tipo",
        ),
        CheckConstraint(
            "estado IN ('activa', 'pagada', 'cancelada')", name="ck_deuda_estado"
        ),
    )


class CuotaDeuda(Base):
    __tablename__ = "cuotas_deuda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deuda_id: Mapped[int] = mapped_column(
        ForeignKey("deudas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vence_en: Mapped[date] = mapped_column(Date, nullable=False)
    pagada: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # Gasto creado al pagar la cuota (trazabilidad)
    transaccion_id: Mapped[int | None] = mapped_column(
        ForeignKey("transacciones.id", ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint("deuda_id", "numero", name="uq_cuota_deuda_numero"),
        CheckConstraint("monto > 0", name="ck_cuota_monto_pos"),
    )
