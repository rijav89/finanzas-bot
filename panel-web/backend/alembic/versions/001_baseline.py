"""Baseline: esquema existente del bot tal cual está en producción (2026-08-14).

En producción NO se ejecuta: se marca con `alembic stamp 001` (las tablas ya existen).
Este upgrade solo sirve para levantar un entorno nuevo (staging/tests) desde cero.

Revision ID: 001
Revises:
Create Date: 2026-08-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("telegram_id", sa.BigInteger, nullable=False, unique=True),
    )
    op.create_table(
        "cuentas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("nombre", sa.Text, nullable=False),
        sa.Column("saldo_inicial", sa.Numeric, server_default=sa.text("0")),
        sa.Column("es_principal", sa.Boolean, server_default=sa.text("false")),
        sa.Column("activa", sa.Boolean, server_default=sa.text("true")),
    )
    op.create_table(
        "transacciones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("monto", sa.Numeric, nullable=False),
        sa.Column("medio", sa.Text),
        sa.Column("descripcion", sa.Text),
        sa.Column("categoria", sa.Text),
        sa.Column("destinatario", sa.Text, server_default=sa.text("'No detectado'")),
        sa.Column("fecha_voucher", sa.Text, server_default=sa.text("'No detectada'")),
        sa.Column("fecha", sa.TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("cuenta_id", sa.Integer, sa.ForeignKey("cuentas.id")),
    )
    op.create_table(
        "ingresos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("monto", sa.Numeric, nullable=False),
        sa.Column("descripcion", sa.Text),
        sa.Column("categoria", sa.Text, server_default=sa.text("'Ingreso'")),
        sa.Column("fecha", sa.TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("cuenta_id", sa.Integer, sa.ForeignKey("cuentas.id")),
    )
    op.create_table(
        "pagos_fijos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("monto", sa.Numeric, nullable=False),
        sa.Column("dia_mes", sa.Integer, nullable=False),
        sa.Column("categoria", sa.Text, server_default=sa.text("'Servicios'")),
        sa.Column("activo", sa.Boolean, server_default=sa.text("true")),
        sa.Column("cuenta_id", sa.Integer, sa.ForeignKey("cuentas.id")),
        sa.CheckConstraint("dia_mes BETWEEN 1 AND 31", name="pagos_fijos_dia_mes_check"),
    )


def downgrade() -> None:
    op.drop_table("pagos_fijos")
    op.drop_table("ingresos")
    op.drop_table("transacciones")
    op.drop_table("cuentas")
    op.drop_table("usuarios")
