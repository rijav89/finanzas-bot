#!/usr/bin/env python3
"""Genera un código de vinculación web para un usuario de Telegram (CLI, servidor del bot).

Uso:
    .venv/bin/python deploy/generar_codigo_vinculacion.py <telegram_id>

Imprime el código EN CLARO una sola vez (solo en la terminal del operador);
en BD queda únicamente el SHA-256 con TTL de 10 minutos.
En F4 este flujo se reemplaza por el comando /vincular del propio bot.
"""
import hashlib
import secrets
import sys

BOT_ENV = "/home/ubuntu/finanzas-bot/.env"
# Sin caracteres ambiguos (0/O, 1/I/L)
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
TTL_MINUTOS = 10


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print(__doc__)
        return 1
    telegram_id = int(sys.argv[1])

    sys.path.insert(0, "/home/ubuntu/finanzas-bot/panel-web/backend/deploy")
    import psycopg
    from alembic_desde_bot_env import leer_db_config

    codigo = "".join(secrets.choice(ALFABETO) for _ in range(8))
    codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()

    with psycopg.connect(leer_db_config(BOT_ENV)) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM usuarios WHERE telegram_id = %s", (telegram_id,))
            fila = cur.fetchone()
            if fila is None:
                print(f"No existe usuario con telegram_id {telegram_id}")
                return 1
            usuario_id = fila[0]
            cur.execute(
                """
                INSERT INTO codigos_vinculacion (usuario_id, codigo_hash, expira_en)
                VALUES (%s, %s, NOW() + make_interval(mins => %s))
                """,
                (usuario_id, codigo_hash, TTL_MINUTOS),
            )
        conn.commit()

    print(f"Código de vinculación para telegram_id {telegram_id} (usuario {usuario_id}):")
    print(f"\n    {codigo}\n")
    print(f"Vence en {TTL_MINUTOS} minutos. Ingresarlo en el panel web tras iniciar sesión.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
