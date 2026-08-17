"""Préstamos entre personas: movimientos que mueven el saldo sin ser ingreso ni gasto.

Un préstamo no es plata que ganaste ni que gastaste: cambia de manos, no de dueño.
Si las devoluciones contaran como gasto, se duplicaría lo que ya registraste al
comprar con esa plata. Por eso el circuito completo (entregar, recibir, cobrar,
devolver) usa la categoría de sistema `Prestamo`, excluida de los totales igual que
`Transferencia` pero visible en el historial y en el saldo.

`cuotas_deuda` gana `ingreso_id`: cuando te devuelven un préstamo que otorgaste, el
movimiento es un ingreso, y esa tabla vive en `ingresos`, no en `transacciones`.

Revision ID: 005
Revises: 004
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cuotas_deuda", sa.Column("ingreso_id", sa.Integer))
    op.create_foreign_key(
        "fk_cuota_ingreso", "cuotas_deuda", "ingresos", ["ingreso_id"], ["id"], ondelete="SET NULL"
    )

    op.bulk_insert(
        sa.table(
            "categorias",
            sa.column("usuario_id", sa.Integer),
            sa.column("nombre", sa.Text),
            sa.column("es_sistema", sa.Boolean),
            sa.column("tipo", sa.Text),
        ),
        [{"usuario_id": None, "nombre": "Prestamo", "es_sistema": True, "tipo": "ambos"}],
    )


def downgrade() -> None:
    op.execute("DELETE FROM categorias WHERE usuario_id IS NULL AND nombre = 'Prestamo'")
    op.drop_constraint("fk_cuota_ingreso", "cuotas_deuda", type_="foreignkey")
    op.drop_column("cuotas_deuda", "ingreso_id")
