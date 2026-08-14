"""Modelos SQLAlchemy — fuente de verdad del esquema para Alembic.

Las tablas existentes del bot (usuarios, cuentas, transacciones, ingresos,
pagos_fijos) se mapean TAL CUAL están en producción; el bot sigue escribiendo
con psycopg plano y no importa este paquete.
"""

from .base import Base
from .usuarios import Usuario
from .cuentas import Cuenta, MetaAhorro
from .movimientos import Ingreso, Transaccion
from .pagos import PagoFijo
from .categorias import CATEGORIA_TRANSFERENCIA, CATEGORIAS_SISTEMA, Categoria
from .auth_links import CodigoVinculacion, VinculoAuth
from .deudas import CuotaDeuda, Deuda
from .presupuestos import Presupuesto
from .perfil import Meta, PerfilFinanciero
from .insights import InsightIA

__all__ = [
    "Base",
    "Usuario",
    "Cuenta",
    "MetaAhorro",
    "Transaccion",
    "Ingreso",
    "PagoFijo",
    "Categoria",
    "CATEGORIAS_SISTEMA",
    "CATEGORIA_TRANSFERENCIA",
    "VinculoAuth",
    "CodigoVinculacion",
    "Deuda",
    "CuotaDeuda",
    "Presupuesto",
    "PerfilFinanciero",
    "Meta",
    "InsightIA",
]
