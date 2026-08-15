from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CuentaCrear(_Estricto):
    nombre: str = Field(min_length=1, max_length=80)
    tipo: Literal["corriente", "ahorro"] = "corriente"
    saldo_inicial: Decimal = Field(default=Decimal("0"), ge=0, le=1_000_000)
    es_principal: bool = False


class CuentaEditar(_Estricto):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    tipo: Literal["corriente", "ahorro"] | None = None
    saldo_inicial: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    es_principal: bool | None = None


class CuentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo: str
    saldo_inicial: Decimal | None
    es_principal: bool | None
    activa: bool | None
