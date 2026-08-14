"""Integridad de montos: CHECK monto > 0 en transacciones e ingresos.

(El pre-paso verificó que monto ya es NUMERIC y telegram_id ya tiene UNIQUE,
así que los fixes de tipo previstos originalmente no fueron necesarios.)

NOT VALID + VALIDATE: el ADD CONSTRAINT no escanea la tabla (lock breve);
VALIDATE escanea sin bloquear escrituras. El bot no inserta montos <= 0
(valida en NLP/OCR), así que VALIDATE no debería fallar.

Revision ID: 002
Revises: 001
Create Date: 2026-08-14

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE transacciones ADD CONSTRAINT ck_trans_monto_pos CHECK (monto > 0) NOT VALID"
    )
    op.execute(
        "ALTER TABLE ingresos ADD CONSTRAINT ck_ing_monto_pos CHECK (monto > 0) NOT VALID"
    )
    op.execute("ALTER TABLE transacciones VALIDATE CONSTRAINT ck_trans_monto_pos")
    op.execute("ALTER TABLE ingresos VALIDATE CONSTRAINT ck_ing_monto_pos")


def downgrade() -> None:
    op.execute("ALTER TABLE transacciones DROP CONSTRAINT ck_trans_monto_pos")
    op.execute("ALTER TABLE ingresos DROP CONSTRAINT ck_ing_monto_pos")
