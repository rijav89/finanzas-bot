#!/usr/bin/env python3
"""Ejecuta Alembic tomando las credenciales del .env del bot, sin sacarlas del servidor.

Uso (en el servidor del bot, desde panel-web/backend/):
    .venv/bin/python deploy/alembic_desde_bot_env.py stamp 001
    .venv/bin/python deploy/alembic_desde_bot_env.py upgrade 002
    .venv/bin/python deploy/alembic_desde_bot_env.py current

Lee DB_CONFIG (conninfo psycopg: URL o pares clave=valor) de /home/ubuntu/finanzas-bot/.env,
lo convierte a URL SQLAlchemy con driver psycopg y lanza el CLI de alembic con
ALEMBIC_DATABASE_URL en el entorno. El secreto nunca se imprime ni se escribe a disco.
"""
import os
import subprocess
import sys

BOT_ENV = "/home/ubuntu/finanzas-bot/.env"


def leer_db_config(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea.startswith("DB_CONFIG="):
                valor = linea.split("=", 1)[1].strip()
                if (valor.startswith("'") and valor.endswith("'")) or (
                    valor.startswith('"') and valor.endswith('"')
                ):
                    valor = valor[1:-1]
                return valor
    raise SystemExit(f"DB_CONFIG no encontrado en {path}")


def a_url_sqlalchemy(conninfo: str) -> str:
    if conninfo.startswith("postgresql://"):
        return conninfo.replace("postgresql://", "postgresql+psycopg://", 1)
    if conninfo.startswith("postgres://"):
        return conninfo.replace("postgres://", "postgresql+psycopg://", 1)
    # Formato clave=valor separado por espacios
    campos = dict(par.split("=", 1) for par in conninfo.split() if "=" in par)
    user = campos.get("user", "")
    password = campos.get("password", "")
    host = campos.get("host", "localhost")
    port = campos.get("port", "5432")
    dbname = campos.get("dbname", "postgres")
    sslmode = campos.get("sslmode", "require")
    from urllib.parse import quote

    return (
        f"postgresql+psycopg://{quote(user)}:{quote(password)}@{host}:{port}/{dbname}"
        f"?sslmode={sslmode}"
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = a_url_sqlalchemy(leer_db_config(BOT_ENV))
    venv_alembic = os.path.join(os.path.dirname(sys.executable), "alembic")
    return subprocess.call([venv_alembic, *sys.argv[1:]], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
