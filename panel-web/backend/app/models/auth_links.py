import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Index, Integer, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class VinculoAuth(Base):
    """Vínculo 1:1 entre el usuario del bot (usuarios.id) y Supabase Auth (auth.users.id)."""

    __tablename__ = "vinculos_auth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    auth_uid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True)
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class CodigoVinculacion(Base):
    """Código de un solo uso emitido por el bot para vincular Telegram con la cuenta web.

    Se guarda solo el SHA-256 del código, nunca el código en claro. TTL 10 minutos.
    """

    __tablename__ = "codigos_vinculacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    codigo_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_codvinc_hash_vigente", "codigo_hash", postgresql_where=text("NOT usado")),
    )
