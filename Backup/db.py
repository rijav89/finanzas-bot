import psycopg
from config import DB_CONNECTION


def get_connection():
    return psycopg.connect(DB_CONNECTION)


def obtener_o_crear_usuario(telegram_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM usuarios WHERE telegram_id = %s",
        (telegram_id,)
    )

    usuario = cur.fetchone()

    if usuario is None:

        cur.execute(
            "INSERT INTO usuarios (telegram_id) VALUES (%s) RETURNING id",
            (telegram_id,)
        )

        usuario_id = cur.fetchone()[0]

    else:
        usuario_id = usuario[0]

    conn.commit()

    cur.close()
    conn.close()

    return usuario_id


def guardar_transaccion(usuario_id, monto, medio, descripcion, categoria):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO transacciones
        (usuario_id, monto, medio, descripcion, categoria)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (usuario_id, monto, medio, descripcion, categoria)
    )

    conn.commit()

    cur.close()
    conn.close()


def obtener_total_mes(usuario_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COALESCE(SUM(monto),0)
        FROM transacciones
        WHERE usuario_id=%s
        AND date_trunc('month',fecha)=date_trunc('month',NOW())
        """,
        (usuario_id,)
    )

    total = cur.fetchone()[0]

    cur.close()
    conn.close()

    return total