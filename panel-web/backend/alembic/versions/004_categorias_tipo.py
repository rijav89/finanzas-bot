"""Catálogo de categorías: separa gasto de ingreso y cubre los huecos del seed original.

Tres cosas, todas aditivas para el bot:
1. Columna `tipo` — hasta ahora la tabla solo tenía categorías de gasto, así que el
   panel no podía ofrecer un catálogo de ingresos y todo entraba como 'Ingreso'.
2. 4 categorías de gasto nuevas (Vivienda, Suscripciones, Regalos, Impuestos) y 7 de
   ingreso. No se agrega 'Deudas': los pagos de cuotas ya se registran desde su propio
   módulo y una categoría homónima duplicaría el mismo dinero en el diagrama de flujo.
3. 'Transporte' pasa a 'Transporte y vehiculo'. Como `transacciones.categoria` es TEXT
   sin FK, hay que renombrar también los movimientos ya guardados o quedan huérfanos.

Revision ID: 004
Revises: 003
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIAS_GASTO_NUEVAS = ["Vivienda", "Suscripciones", "Regalos", "Impuestos"]

CATEGORIAS_INGRESO = [
    "Sueldo", "Freelance", "Negocio", "Regalo recibido",
    "Reembolso", "Intereses", "Otros ingresos",
]

RENOMBRE = ("Transporte", "Transporte y vehiculo")

# El bot guardaba todos los ingresos con esta etiqueta genérica por defecto.
INGRESO_LEGACY = ("Ingreso", "Otros ingresos")


def upgrade() -> None:
    op.add_column(
        "categorias",
        sa.Column("tipo", sa.Text, nullable=False, server_default=sa.text("'gasto'")),
    )
    op.create_check_constraint(
        "ck_categoria_tipo", "categorias", "tipo IN ('gasto', 'ingreso', 'ambos')"
    )
    # Transferencia no es ni gasto ni ingreso: aparece en ambos lados de un traslado
    op.execute("UPDATE categorias SET tipo = 'ambos' WHERE nombre = 'Transferencia'")

    op.bulk_insert(
        sa.table(
            "categorias",
            sa.column("usuario_id", sa.Integer),
            sa.column("nombre", sa.Text),
            sa.column("es_sistema", sa.Boolean),
            sa.column("tipo", sa.Text),
        ),
        [
            {"usuario_id": None, "nombre": n, "es_sistema": True, "tipo": "gasto"}
            for n in CATEGORIAS_GASTO_NUEVAS
        ]
        + [
            {"usuario_id": None, "nombre": n, "es_sistema": True, "tipo": "ingreso"}
            for n in CATEGORIAS_INGRESO
        ],
    )

    _renombrar(*RENOMBRE)
    op.execute(
        sa.text("UPDATE ingresos SET categoria = :nuevo WHERE categoria = :viejo").bindparams(
            viejo=INGRESO_LEGACY[0], nuevo=INGRESO_LEGACY[1]
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE ingresos SET categoria = :nuevo WHERE categoria = :viejo").bindparams(
            viejo=INGRESO_LEGACY[1], nuevo=INGRESO_LEGACY[0]
        )
    )
    _renombrar(RENOMBRE[1], RENOMBRE[0])

    nombres = CATEGORIAS_GASTO_NUEVAS + CATEGORIAS_INGRESO
    op.execute(
        sa.text("DELETE FROM categorias WHERE usuario_id IS NULL AND nombre = ANY(:nombres)")
        .bindparams(sa.bindparam("nombres", value=nombres, type_=sa.ARRAY(sa.Text)))
    )
    op.drop_constraint("ck_categoria_tipo", "categorias", type_="check")
    op.drop_column("categorias", "tipo")


def _renombrar(viejo: str, nuevo: str) -> None:
    """Renombra la fila del catálogo y arrastra los movimientos que la referencian."""
    for sql in (
        "UPDATE categorias SET nombre = :nuevo WHERE nombre = :viejo AND usuario_id IS NULL",
        "UPDATE transacciones SET categoria = :nuevo WHERE categoria = :viejo",
        "UPDATE ingresos SET categoria = :nuevo WHERE categoria = :viejo",
    ):
        op.execute(sa.text(sql).bindparams(viejo=viejo, nuevo=nuevo))
