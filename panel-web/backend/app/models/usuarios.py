from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Usuario(Base):
    """Tabla existente del bot — mapeada tal cual (usuarios_telegram_id_key ya existe en prod)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
