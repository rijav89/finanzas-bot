#!/usr/bin/env bash
# Le pone contraseña al rol `panel_web` y apunta el panel a ese rol.
#
# Se corre en el servidor, una sola vez, DESPUÉS de la migración 007. La contraseña se
# genera acá y solo viaja de este proceso al .env: nunca pasa por el repositorio ni por
# la línea de comandos, donde un `ps` la dejaría a la vista.
#
# `ALEMBIC_DATABASE_URL` sigue apuntando a `postgres`, que es quien tiene permiso para
# crear tablas: las migraciones no las corre el panel.
set -euo pipefail

BACKEND=/home/ubuntu/finanzas-bot/panel-web/backend
ENV="$BACKEND/.env"

# shellcheck disable=SC1090
set -a; . "$ENV"; set +a

ADMIN="${ALEMBIC_DATABASE_URL/postgresql+psycopg:\/\//postgresql://}"

# El usuario del pooler lleva el proyecto pegado: <rol>.<ref>
REF=$(sed -E 's#.*://([^:]+):.*#\1#' <<<"$ADMIN" | cut -d. -f2)
HOST=$(sed -E 's#.*@([^:/]+).*#\1#' <<<"$ADMIN")
PUERTO=$(sed -E 's#.*@[^:]+:([0-9]+).*#\1#' <<<"$ADMIN")

CLAVE=$(openssl rand -base64 33 | tr -d '/+=' | head -c 40)

# Por stdin y no con -c: psql solo interpola :'variables' en lo que lee del script,
# y así la contraseña tampoco aparece en la línea de comandos.
psql "$ADMIN" -v ON_ERROR_STOP=1 -q -v clave="$CLAVE" <<'SQL'
ALTER ROLE panel_web WITH PASSWORD :'clave';
SQL

NUEVA_URL="postgresql+asyncpg://panel_web.${REF}:${CLAVE}@${HOST}:${PUERTO}/postgres"

# Probar ANTES de tocar el .env: si el pooler no acepta roles propios, mejor
# enterarse acá que con el panel caído.
echo "Probando la conexión como panel_web…"
PGPASSWORD="$CLAVE" psql -q -h "$HOST" -p "$PUERTO" -U "panel_web.${REF}" -d postgres \
  -v ON_ERROR_STOP=1 \
  -c "SELECT current_user, (SELECT count(*) FROM transacciones) AS filas_visibles"

echo "Comprobando que NO pueda romper nada…"
if PGPASSWORD="$CLAVE" psql -q -h "$HOST" -p "$PUERTO" -U "panel_web.${REF}" -d postgres \
     -c "CREATE TABLE deberia_fallar (id int)" 2>/dev/null; then
  echo "ERROR: el rol pudo crear una tabla. Abortando sin tocar el .env." >&2
  exit 1
fi
echo "  ok: no puede crear tablas"

cp "$ENV" "$ENV.bak.$(date +%Y%m%d%H%M%S)"
chmod 600 "$ENV".bak.*
grep -v '^DATABASE_URL=' "$ENV" > "$ENV.nuevo"
echo "DATABASE_URL=${NUEVA_URL}" >> "$ENV.nuevo"
mv "$ENV.nuevo" "$ENV"
chmod 600 "$ENV"

echo
echo "Listo. DATABASE_URL apunta a panel_web (ALEMBIC_DATABASE_URL sigue en postgres)."
echo "Copia previa del .env guardada al lado, por si hay que volver atrás."
