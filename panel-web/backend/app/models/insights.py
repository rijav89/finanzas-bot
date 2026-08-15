from datetime import date, datetime

from sqlalchemy import (
    JSON, TIMESTAMP, Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, Text, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

JsonPortable = JSON().with_variant(JSONB(), "postgresql")

from .base import Base


class InsightIA(Base):
    """Insight generado por el job batch semanal (qwen-plus). El frontend solo lee."""

    __tablename__ = "insights_ia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    # 'patron_gasto' | 'alerta_presupuesto' | 'tendencia' | 'recomendacion'
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    # 'info' | 'atencion' | 'critico' → semáforo en la UI
    severidad: Mapped[str] = mapped_column(Text, nullable=False)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fin: Mapped[date] = mapped_column(Date, nullable=False)
    # {detalle, metrica, delta_pct, categoria, evidencia}
    payload: Mapped[dict] = mapped_column(JsonPortable, nullable=False)
    modelo: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_usados: Mapped[int | None] = mapped_column(Integer)
    leido: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_insights_usuario_fecha", "usuario_id", "creado_en"),
        CheckConstraint(
            "severidad IN ('info', 'atencion', 'critico')", name="ck_insight_severidad"
        ),
    )
