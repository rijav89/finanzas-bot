"""Rol `panel_web` de privilegio mínimo para la API.

Hasta ahora el panel se conectaba como `postgres`, dueño de todo: una inyección SQL o
el servidor comprometido daban control total de la base, incluido borrar tablas. Este
rol solo puede leer y escribir filas en las tablas de la aplicación.

Qué NO puede: DDL de ningún tipo, tocar `alembic_version` (las migraciones siguen
corriendo como `postgres`), ni asomarse al esquema `auth` de Supabase.

Sobre las políticas: la 006 dejó RLS activo en todo, y un rol sin BYPASSRLS no ve nada
si no hay política que lo habilite. Se crean permisivas —`USING (true)`— porque hoy el
aislamiento entre usuarios lo dan los filtros `usuario_id` de cada consulta y los tests
anti-IDOR. Filtrar acá costaría un `SET LOCAL` por transacción, es decir un viaje extra
a Supabase (~150 ms) en cada petición, y no protegería de un `.env` robado: quien tenga
la credencial puede fijar el GUC él mismo.

Si algún día hay varios usuarios reales, el cambio es reemplazar `USING (true)` por
`usuario_id = current_setting('app.usuario_id')::int`; el código del backend ya trae
`_fijar_guc_rls` esperando detrás de la variable `RLS_ACTIVO`.

La contraseña NO se define acá: la genera `deploy/crear_rol_panel_web.sh` en el
servidor, para que ningún secreto pase por el repositorio.

Revision ID: 007
Revises: 006
Create Date: 2026-08-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROL = "panel_web"

#: Alembic corre como `postgres`; el panel no tiene por qué ver su propia bitácora.
FUERA_DE_ALCANCE = ("alembic_version",)


def upgrade() -> None:
    # Sin contraseña: el rol existe pero no puede iniciar sesión hasta que el script
    # del servidor le ponga una. Así el repo nunca contiene una credencial.
    op.execute(f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROL}') THEN
            CREATE ROLE {ROL} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                              NOINHERIT NOBYPASSRLS NOREPLICATION;
          END IF;
        END $$;
    """)

    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROL}")

    excluidas = ", ".join(f"'{t}'" for t in FUERA_DE_ALCANCE)
    op.execute(f"""
        DO $$
        DECLARE t record;
        BEGIN
          FOR t IN
            SELECT c.relname FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
              AND c.relname NOT IN ({excluidas})
          LOOP
            EXECUTE format(
              'GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO {ROL}', t.relname
            );
            -- Sin política no vería nada: la 006 dejó RLS activo en todas
            EXECUTE format('DROP POLICY IF EXISTS {ROL}_acceso ON public.%I', t.relname);
            EXECUTE format(
              'CREATE POLICY {ROL}_acceso ON public.%I FOR ALL TO {ROL} '
              'USING (true) WITH CHECK (true)', t.relname
            );
          END LOOP;
        END $$;
    """)

    # Los INSERT necesitan avanzar las secuencias de los id
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROL}")

    # Que una tabla futura no nazca invisible para el panel
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROL}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {ROL}"
    )


def downgrade() -> None:
    op.execute(f"""
        DO $$
        DECLARE t record;
        BEGIN
          FOR t IN
            SELECT c.relname FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
          LOOP
            EXECUTE format('DROP POLICY IF EXISTS {ROL}_acceso ON public.%I', t.relname);
          END LOOP;
        END $$;
    """)
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE ALL ON TABLES FROM {ROL}"
    )
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {ROL}")
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROL}")
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {ROL}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {ROL}")
    # El rol no se elimina: puede seguir siendo dueño de conexiones abiertas
