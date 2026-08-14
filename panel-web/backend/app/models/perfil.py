from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PerfilFinanciero(Base):
    """Perfil declarado por el usuario en la web; sirve de contexto para los insights de IA."""

    __tablename__ = "perfiles_financieros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    ingreso_mensual_declarado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    moneda: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'PEN'"))
    perfil_riesgo: Mapped[str | None] = mapped_column(Text)
    contexto_ia: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Meta(Base):
    __tablename__ = "metas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    # 'ahorro' | 'reduccion_gasto' | 'pago_deuda'
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    monto_objetivo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    fecha_objetivo: Mapped[date | None] = mapped_column(Date)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="SET NULL"))
    cumplida: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('ahorro', 'reduccion_gasto', 'pago_deuda')", name="ck_meta_tipo"
        ),
    )
