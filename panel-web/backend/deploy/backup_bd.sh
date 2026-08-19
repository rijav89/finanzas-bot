#!/usr/bin/env bash
# Backup semanal de la base a disco local, comprimido y con rotación.
#
# Supabase gratuito no guarda backups propios: si la base se corrompe o alguien borra
# una tabla, esto es lo único que queda. El volcado se hace con pg_dump 17, porque el
# servidor corre 17.6 y el cliente 16 de Ubuntu se niega a volcar una versión mayor.
#
# La contraseña sale del .env del panel (permisos 600) y nunca aparece en la línea de
# comandos, donde cualquiera con `ps` podría leerla.
set -euo pipefail

BACKEND=/home/ubuntu/finanzas-bot/panel-web/backend
DESTINO=/home/ubuntu/backups
SEMANAS=8

# shellcheck disable=SC1091
set -a; . "$BACKEND/.env"; set +a

# SQLAlchemy usa un prefijo que libpq no entiende
URL="${ALEMBIC_DATABASE_URL/postgresql+psycopg:\/\//postgresql://}"

mkdir -p "$DESTINO"
chmod 700 "$DESTINO"

ARCHIVO="$DESTINO/finanzasbot_$(date +%Y%m%d).sql.gz"

# --no-owner y --no-acl: al restaurar en otro proyecto los roles de Supabase no existen
pg_dump "$URL" \
  --schema=public \
  --no-owner --no-acl \
  --format=plain \
  | gzip -9 > "$ARCHIVO.parcial"

# Renombrar al final: un backup a medias nunca queda con nombre de backup bueno
mv "$ARCHIVO.parcial" "$ARCHIVO"
chmod 600 "$ARCHIVO"

# Rotación: se conservan las últimas N semanas
find "$DESTINO" -name 'finanzasbot_*.sql.gz' -type f -printf '%T@ %p\n' \
  | sort -rn | tail -n +$((SEMANAS + 1)) | cut -d' ' -f2- | xargs -r rm -f

TAMANO=$(du -h "$ARCHIVO" | cut -f1)
TABLAS=$(zcat "$ARCHIVO" | grep -c '^CREATE TABLE' || true)
echo "[backup] $(TZ=America/Lima date '+%Y-%m-%d %H:%M') Lima · $ARCHIVO · $TAMANO · $TABLAS tablas"
