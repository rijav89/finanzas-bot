"""Schemas de los módulos nuevos: categorías, presupuestos, deudas, ahorros,
recurrentes, perfil y metas. Pydantic v2 estricto (extra='forbid')."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MONTO_MAX = Decimal("1000000")


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── Categorías ───────────────────────────────────────────────────────────────

class CategoriaCrear(_Estricto):
    nombre: str = Field(min_length=1, max_length=40)
    icono: str | None = Field(default=None, max_length=16)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class CategoriaEditar(_Estricto):
    nombre: str | None = Field(default=None, min_length=1, max_length=40)
    icono: str | None = Field(default=None, max_length=16)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    activa: bool | None = None


# ── Presupuestos ─────────────────────────────────────────────────────────────

class PresupuestoItem(_Estricto):
    categoria: str = Field(min_length=1, max_length=40)
    monto_limite: Decimal = Field(gt=0, le=MONTO_MAX)


class PresupuestosUpsert(_Estricto):
    anio: int = Field(ge=2020, le=2100)
    mes: int = Field(ge=1, le=12)
    items: list[PresupuestoItem] = Field(max_length=60)


# ── Deudas ───────────────────────────────────────────────────────────────────

TipoDeuda = Literal["prestamo_recibido", "prestamo_otorgado", "tarjeta"]


class DeudaCrear(_Estricto):
    tipo: TipoDeuda
    acreedor: str = Field(min_length=1, max_length=120)
    monto_total: Decimal = Field(gt=0, le=MONTO_MAX)
    tasa_interes: Decimal | None = Field(default=None, ge=0, le=999)
    num_cuotas: int | None = Field(default=None, ge=1, le=600)
    fecha_inicio: date
    cuenta_id: int | None = None
    #: Si se envía, genera el cronograma de cuotas iguales automáticamente.
    generar_cuotas: bool = True


class DeudaEditar(_Estricto):
    acreedor: str | None = Field(default=None, min_length=1, max_length=120)
    tasa_interes: Decimal | None = Field(default=None, ge=0, le=999)
    estado: Literal["activa", "pagada", "cancelada"] | None = None
    cuenta_id: int | None = None


class PagarCuota(_Estricto):
    """Al pagar se registra un gasto real; la cuenta puede diferir de la de la deuda."""
    cuenta_id: int | None = None
    fecha: date | None = None


# ── Ahorros ──────────────────────────────────────────────────────────────────

class MetaAhorroUpsert(_Estricto):
    monto_objetivo: Decimal = Field(gt=0, le=MONTO_MAX)
    fecha_objetivo: date | None = None


# ── Recurrentes (pagos_fijos extendida) ──────────────────────────────────────

Frecuencia = Literal["mensual", "semanal", "anual"]


class RecurrenteCrear(_Estricto):
    descripcion: str = Field(min_length=1, max_length=200)
    monto: Decimal = Field(gt=0, le=MONTO_MAX)
    dia_mes: int = Field(ge=1, le=31)
    categoria: str = Field(default="Servicios", min_length=1, max_length=40)
    cuenta_id: int | None = None
    frecuencia: Frecuencia = "mensual"
    fecha_fin: date | None = None


class RecurrenteEditar(_Estricto):
    descripcion: str | None = Field(default=None, min_length=1, max_length=200)
    monto: Decimal | None = Field(default=None, gt=0, le=MONTO_MAX)
    dia_mes: int | None = Field(default=None, ge=1, le=31)
    categoria: str | None = Field(default=None, min_length=1, max_length=40)
    cuenta_id: int | None = None
    frecuencia: Frecuencia | None = None
    fecha_fin: date | None = None
    activo: bool | None = None


# ── Perfil y metas ───────────────────────────────────────────────────────────

class PerfilUpsert(_Estricto):
    ingreso_mensual_declarado: Decimal | None = Field(default=None, ge=0, le=MONTO_MAX)
    moneda: str = Field(default="PEN", min_length=3, max_length=3)
    perfil_riesgo: Literal["conservador", "moderado", "arriesgado"] | None = None
    contexto_ia: dict = Field(default_factory=dict)


TipoMeta = Literal["ahorro", "reduccion_gasto", "pago_deuda"]


class MetaCrear(_Estricto):
    titulo: str = Field(min_length=1, max_length=200)
    tipo: TipoMeta
    monto_objetivo: Decimal | None = Field(default=None, gt=0, le=MONTO_MAX)
    fecha_objetivo: date | None = None
    cuenta_id: int | None = None


class MetaEditar(_Estricto):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    monto_objetivo: Decimal | None = Field(default=None, gt=0, le=MONTO_MAX)
    fecha_objetivo: date | None = None
    cuenta_id: int | None = None
    cumplida: bool | None = None
