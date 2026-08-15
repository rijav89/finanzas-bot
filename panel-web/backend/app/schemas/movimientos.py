from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


MONTO_MAX = Decimal("1000000")


class GastoCrear(_Estricto):
    monto: Decimal = Field(gt=0, le=MONTO_MAX)
    categoria: str = Field(min_length=1, max_length=40)
    cuenta_id: int
    medio: str | None = Field(default=None, max_length=40)
    descripcion: str | None = Field(default=None, max_length=300)
    fecha: date | None = None  # None = hoy


class IngresoCrear(_Estricto):
    monto: Decimal = Field(gt=0, le=MONTO_MAX)
    cuenta_id: int
    categoria: str = Field(default="Ingreso", min_length=1, max_length=40)
    descripcion: str | None = Field(default=None, max_length=300)
    fecha: date | None = None


class MovimientoEditar(_Estricto):
    monto: Decimal | None = Field(default=None, gt=0, le=MONTO_MAX)
    categoria: str | None = Field(default=None, min_length=1, max_length=40)
    descripcion: str | None = Field(default=None, max_length=300)
    cuenta_id: int | None = None


class TransferenciaCrear(_Estricto):
    origen_id: int
    destino_id: int
    monto: Decimal = Field(gt=0, le=MONTO_MAX)


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: Literal["gasto", "ingreso"]
    monto: Decimal
    categoria: str | None
    descripcion: str | None
    medio: str | None = None
    destinatario: str | None = None
    fecha: datetime | None
    cuenta_id: int | None
