"""Cierra la API pública de PostgREST sobre el esquema `public`.

El proyecto Supabase expone automáticamente cada tabla de `public` por HTTP, y los
roles `anon` y `authenticated` traían GRANT de SELECT/INSERT/UPDATE/DELETE sobre todas
— privilegios por defecto del proyecto, no algo que se haya escrito acá. Las tablas que
el bot creó en su día sí tenían RLS; las once que agregó Alembic, no. Resultado
verificado por HTTP el 2026-08-19: `insights_ia`, `vinculos_auth`,
`codigos_vinculacion` y `categorias` devolvían filas a cualquiera con la URL del
proyecto y la clave anónima.

Lo más serio no era la lectura sino la escritura: con INSERT sobre `vinculos_auth`
cualquiera podía atar su cuenta de Supabase Auth al `usuario_id` ajeno y después leer
esas finanzas por la vía legítima del panel, saltándose las tablas que sí tenían RLS.

Dos candados, a propósito:
1. RLS activado en todas las tablas. Sin políticas, nadie pasa; el bot y el panel se
   conectan con el rol `postgres`, que tiene BYPASSRLS, así que no cambia nada para
   ellos (verificado: rolbypassrls = true).
2. REVOKE a `anon` y `authenticated`, más ALTER DEFAULT PRIVILEGES para que las tablas
   que se creen mañana no nazcan otra vez abiertas.

Con uno solo alcanzaría; con los dos, un error futuro en una política no reabre la
puerta. Esto NO reemplaza las políticas por usuario del plan (rol `panel_web`): es el
paso de cerrar la puerta de calle.

Revision ID: 006
Revises: 005
Create Date: 2026-08-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLES_PUBLICOS = ("anon", "authenticated")


def upgrade() -> None:
    # 1 · RLS en todo lo que viva en public, incluidas las tablas del bot
    op.execute("""
        DO $$
        DECLARE t record;
        BEGIN
          FOR t IN
            SELECT c.relname FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity
          LOOP
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.relname);
          END LOOP;
        END $$;
    """)

    # 2 · Quitar los privilegios de los roles que atiende la API pública
    for rol in ROLES_PUBLICOS:
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {rol}")
        op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {rol}")
        op.execute(f"REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM {rol}")
        op.execute(f"REVOKE USAGE ON SCHEMA public FROM {rol}")
        # Sin esto, la próxima tabla que cree Alembic vuelve a nacer con GRANT
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {rol}"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {rol}"
        )


def downgrade() -> None:
    """Reabre la API pública. Existe por simetría, no porque convenga usarlo."""
    for rol in ROLES_PUBLICOS:
        op.execute(f"GRANT USAGE ON SCHEMA public TO {rol}")
        op.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA public TO {rol}")
        op.execute(f"GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {rol}")

    op.execute("""
        DO $$
        DECLARE t record;
        BEGIN
          FOR t IN
            SELECT c.relname FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
          LOOP
            EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t.relname);
          END LOOP;
        END $$;
    """)
