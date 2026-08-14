"""Módulos nuevos del panel: tablas nuevas + columnas aditivas + índices + seed de categorías.

Todo es aditivo: el bot inserta con columnas explícitas y las nuevas tienen DEFAULT,
así que su comportamiento no cambia.

Revision ID: 003
Revises: 002
Create Date: 2026-08-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIAS_SISTEMA = [
    "Comida", "Supermercado", "Transporte", "Servicios", "Salud",
    "Educacion", "Ropa", "Entretenimiento", "Tecnologia", "Finanzas",
    "Mascotas", "Belleza", "Hogar", "Otros", "Transferencia",
]


def upgrade() -> None:
    # --- Columnas aditivas en tablas existentes (el bot las ignora) ---
    op.add_column(
        "cuentas",
        sa.Column("tipo", sa.Text, nullable=False, server_default=sa.text("'corriente'")),
    )
    op.add_column(
        "pagos_fijos",
        sa.Column("frecuencia", sa.Text, nullable=False, server_default=sa.text("'mensual'")),
    )
    op.add_column("pagos_fijos", sa.Column("fecha_fin", sa.Date))
    op.add_column(
        "pagos_fijos",
        sa.Column("auto_registrar", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )
    op.add_column("pagos_fijos", sa.Column("ultimo_registro", sa.Date))

    # --- Vinculación Telegram ↔ Supabase Auth ---
    op.create_table(
        "vinculos_auth",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "usuario_id", sa.Integer,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True,
        ),
        sa.Column("auth_uid", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "creado_en", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "codigos_vinculacion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "usuario_id", sa.Integer,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("codigo_hash", sa.Text, nullable=False),
        sa.Column("expira_en", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("usado", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "creado_en", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_codvinc_hash_vigente", "codigos_vinculacion", ["codigo_hash"],
        postgresql_where=sa.text("NOT usado"),
    )

    # --- Categorías (sistema + por usuario) ---
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id", ondelete="CASCADE")),
        sa.Column("nombre", sa.Text, nullable=False),
        sa.Column("icono", sa.Text),
        sa.Column("color", sa.Text),
        sa.Column("es_sistema", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("activa", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("usuario_id", "nombre", name="uq_categoria_usuario_nombre"),
    )

    # --- Deudas y cuotas ---
    op.create_table(
        "deudas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "usuario_id", sa.Integer,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("acreedor", sa.Text, nullable=False),
        sa.Column("monto_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("tasa_interes", sa.Numeric(6, 3)),
        sa.Column("num_cuotas", sa.Integer),
        sa.Column("fecha_inicio", sa.Date, nullable=False),
        sa.Column("estado", sa.Text, nullable=False, server_default=sa.text("'activa'")),
        sa.Column("cuenta_id", sa.Integer, sa.ForeignKey("cuentas.id")),
        sa.CheckConstraint("monto_total > 0", name="ck_deuda_monto_pos"),
        sa.CheckConstraint(
            "tipo IN ('prestamo_recibido', 'prestamo_otorgado', 'tarjeta')", name="ck_deuda_tipo",
        ),
        sa.CheckConstraint("estado IN ('activa', 'pagada', 'cancelada')", name="ck_deuda_estado"),
    )
    op.create_index("ix_deudas_usuario_id", "deudas", ["usuario_id"])
    op.create_table(
        "cuotas_deuda",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "deuda_id", sa.Integer, sa.ForeignKey("deudas.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("vence_en", sa.Date, nullable=False),
        sa.Column("pagada", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("transaccion_id", sa.Integer, sa.ForeignKey("transacciones.id", ondelete="SET NULL")),
        sa.UniqueConstraint("deuda_id", "numero", name="uq_cuota_deuda_numero"),
        sa.CheckConstraint("monto > 0", name="ck_cuota_monto_pos"),
    )
    op.create_index("ix_cuotas_deuda_deuda_id", "cuotas_deuda", ["deuda_id"])

    # --- Presupuestos ---
    op.create_table(
        "presupuestos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "usuario_id", sa.Integer,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("categoria", sa.Text, nullable=False),
        sa.Column("anio", sa.Integer, nullable=False),
        sa.Column("mes", sa.Integer, nullable=False),
        sa.Column("monto_limite", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("usuario_id", "categoria", "anio", "mes", name="uq_presupuesto_periodo"),
        sa.CheckConstraint("monto_limite > 0", name="ck_presupuesto_monto_pos"),
        sa.CheckConstraint("mes BETWEEN 1 AND 12", name="ck_presupuesto_mes"),
    )
    op.create_index("ix_presupuestos_usuario_id", "presupuestos", ["usuario_id"])

    # --- Perfil financiero y metas ---
    op.create_table(
        "perfiles_financieros",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "usuario_id", sa.Integer,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True,
        ),
        sa.Column("ingreso_mensual_declarado", sa.Numeric(12, 2)),
        sa.Column("moneda", sa.Text, nullable=False, server_default=sa.text("'PEN'")),
        sa.Column("perfil_riesgo", sa.Text),
        sa.Column("contexto_ia", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "actualizado_en", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "metas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "usuario_id", sa.Integer,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("titulo", sa.Text, nullable=False),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("monto_objetivo", sa.Numeric(12, 2)),
        sa.Column("fecha_objetivo", sa.Date),
        sa.Column("cuenta_id", sa.Integer, sa.ForeignKey("cuentas.id", ondelete="SET NULL")),
        sa.Column("cumplida", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("tipo IN ('ahorro', 'reduccion_gasto', 'pago_deuda')", name="ck_meta_tipo"),
    )
    op.create_index("ix_metas_usuario_id", "metas", ["usuario_id"])

    # --- Metas de ahorro (1:1 con cuenta tipo 'ahorro') ---
    op.create_table(
        "metas_ahorro",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "cuenta_id", sa.Integer,
            sa.ForeignKey("cuentas.id", ondelete="CASCADE"), nullable=False, unique=True,
        ),
        sa.Column("monto_objetivo", sa.Numeric(12, 2), nullable=False),
        sa.Column("fecha_objetivo", sa.Date),
        sa.CheckConstraint("monto_objetivo > 0", name="ck_meta_ahorro_monto_pos"),
    )

    # --- Insights IA ---
    op.create_table(
        "insights_ia",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "usuario_id", sa.Integer,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("severidad", sa.Text, nullable=False),
        sa.Column("titulo", sa.Text, nullable=False),
        sa.Column("periodo_inicio", sa.Date, nullable=False),
        sa.Column("periodo_fin", sa.Date, nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("modelo", sa.Text, nullable=False),
        sa.Column("tokens_usados", sa.Integer),
        sa.Column("leido", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "creado_en", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("severidad IN ('info', 'atencion', 'critico')", name="ck_insight_severidad"),
    )
    op.create_index("ix_insights_usuario_fecha", "insights_ia", ["usuario_id", "creado_en"])

    # --- Índices analíticos sobre tablas existentes ---
    # (tablas pequeñas hoy: CREATE INDEX normal, sin CONCURRENTLY, es instantáneo)
    op.create_index(
        "ix_transacciones_usuario_fecha", "transacciones",
        ["usuario_id", sa.literal_column("fecha DESC")],
    )
    op.create_index(
        "ix_ingresos_usuario_fecha", "ingresos",
        ["usuario_id", sa.literal_column("fecha DESC")],
    )
    op.create_index("ix_transacciones_usuario_categoria", "transacciones", ["usuario_id", "categoria"])

    # --- Seed de categorías de sistema ---
    categorias = sa.table(
        "categorias",
        sa.column("usuario_id", sa.Integer),
        sa.column("nombre", sa.Text),
        sa.column("es_sistema", sa.Boolean),
    )
    op.bulk_insert(
        categorias,
        [{"usuario_id": None, "nombre": n, "es_sistema": True} for n in CATEGORIAS_SISTEMA],
    )


def downgrade() -> None:
    op.drop_index("ix_transacciones_usuario_categoria", table_name="transacciones")
    op.drop_index("ix_ingresos_usuario_fecha", table_name="ingresos")
    op.drop_index("ix_transacciones_usuario_fecha", table_name="transacciones")
    op.drop_table("insights_ia")
    op.drop_table("metas_ahorro")
    op.drop_table("metas")
    op.drop_table("perfiles_financieros")
    op.drop_table("presupuestos")
    op.drop_table("cuotas_deuda")
    op.drop_table("deudas")
    op.drop_table("categorias")
    op.drop_table("codigos_vinculacion")
    op.drop_table("vinculos_auth")
    op.drop_column("pagos_fijos", "ultimo_registro")
    op.drop_column("pagos_fijos", "auto_registrar")
    op.drop_column("pagos_fijos", "fecha_fin")
    op.drop_column("pagos_fijos", "frecuencia")
    op.drop_column("cuentas", "tipo")
