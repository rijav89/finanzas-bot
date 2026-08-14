from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    categoria: Mapped[str] = mapped_column(Text, nullable=False)  # join por nombre, como transacciones
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    monto_limite: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("usuario_id", "categoria", "anio", "mes", name="uq_presupuesto_periodo"),
        CheckConstraint("monto_limite > 0", name="ck_presupuesto_monto_pos"),
        CheckConstraint("mes BETWEEN 1 AND 12", name="ck_presupuesto_mes"),
    )
