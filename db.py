"""
db.py — FinanzasBot v2.5
Agrega funciones para historial, resumen por categoría y exportar.
"""

from psycopg_pool import ConnectionPool
from config import DB_CONFIG

db_pool = ConnectionPool(conninfo=DB_CONFIG)

def obtener_o_crear_usuario(telegram_id: int) -> int:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM usuarios WHERE telegram_id=%s", (telegram_id,))
            usuario = cur.fetchone()
            if usuario is None:
                cur.execute("INSERT INTO usuarios (telegram_id) VALUES (%s) RETURNING id", (telegram_id,))
                usuario_id = cur.fetchone()[0]
                conn.commit()
            else:
                usuario_id = usuario[0]
            return usuario_id


def guardar_transaccion(usuario_id, monto, medio, descripcion, categoria, destinatario="No detectado", fecha_voucher="No detectada", fecha=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            if fecha:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher),
                )
            conn.commit()


def actualizar_medio_ultimas(usuario_id: int, medio: str):
    """Actualiza el medio de las últimas transacciones con medio 'Manual' del usuario."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE transacciones SET medio=%s
                WHERE usuario_id=%s AND medio='Manual'
                  AND fecha >= NOW() - INTERVAL '5 minutes'
                """,
                (medio, usuario_id)
            )
            conn.commit()


def obtener_total_mes(usuario_id: int) -> float:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(monto::numeric), 0)
                FROM transacciones
                WHERE usuario_id=%s
                  AND date_trunc('month', fecha) = date_trunc('month', NOW())
                """,
                (usuario_id,),
            )
            total = cur.fetchone()[0]
            return total


def obtener_historial(usuario_id: int, limite: int = 10) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT monto, medio, descripcion, categoria, destinatario, fecha
                FROM transacciones
                WHERE usuario_id=%s
                ORDER BY fecha DESC
                LIMIT %s
                """,
                (usuario_id, limite),
            )
            rows = cur.fetchall()
            return rows


def obtener_resumen_categorias(usuario_id: int) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT categoria, SUM(monto::numeric) as total, COUNT(*) as cantidad
                FROM transacciones
                WHERE usuario_id=%s
                  AND date_trunc('month', fecha) = date_trunc('month', NOW())
                GROUP BY categoria
                ORDER BY total DESC
                """,
                (usuario_id,),
            )
            rows = cur.fetchall()
            return rows


def obtener_transacciones_mes(usuario_id: int) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha
                FROM transacciones
                WHERE usuario_id=%s
                  AND date_trunc('month', fecha) = date_trunc('month', NOW())
                ORDER BY fecha DESC
                """,
                (usuario_id,),
            )
            rows = cur.fetchall()
            return rows


# ── Ingresos ─────────────────────────────────────────────────────────────────

def guardar_ingreso(usuario_id: int, monto: float, descripcion: str, categoria: str = "Ingreso"):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ingresos (usuario_id, monto, descripcion, categoria) VALUES (%s, %s, %s, %s)",
                (usuario_id, monto, descripcion, categoria)
            )
            conn.commit()


def obtener_total_ingresos_mes(usuario_id: int) -> float:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(monto), 0) FROM ingresos
                WHERE usuario_id=%s AND date_trunc('month', fecha) = date_trunc('month', NOW())
                """,
                (usuario_id,)
            )
            total = cur.fetchone()[0]
            return float(total)


def obtener_historial_ingresos(usuario_id: int, limite: int = 10) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT monto, descripcion, categoria, fecha FROM ingresos
                WHERE usuario_id=%s ORDER BY fecha DESC LIMIT %s
                """,
                (usuario_id, limite)
            )
            rows = cur.fetchall()
            return rows


# ── Editar / Eliminar transacciones ──────────────────────────────────────────

def obtener_ultimas_transacciones(usuario_id: int, limite: int = 5) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, monto, descripcion, categoria, medio, fecha
                FROM transacciones WHERE usuario_id=%s
                ORDER BY fecha DESC LIMIT %s
                """,
                (usuario_id, limite)
            )
            rows = cur.fetchall()
            return rows


def eliminar_transaccion(transaccion_id: int, usuario_id: int) -> bool:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM transacciones WHERE id=%s AND usuario_id=%s",
                (transaccion_id, usuario_id)
            )
            eliminado = cur.rowcount > 0
            conn.commit()
            return eliminado


def editar_transaccion(transaccion_id: int, usuario_id: int, monto: float, descripcion: str, categoria: str):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE transacciones SET monto=%s, descripcion=%s, categoria=%s
                WHERE id=%s AND usuario_id=%s
                """,
                (monto, descripcion, categoria, transaccion_id, usuario_id)
            )
            conn.commit()


# ── Pagos fijos ───────────────────────────────────────────────────────────────

def guardar_pago_fijo(usuario_id: int, descripcion: str, monto: float, dia_mes: int, categoria: str = "Servicios"):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pagos_fijos (usuario_id, descripcion, monto, dia_mes, categoria) VALUES (%s, %s, %s, %s, %s)",
                (usuario_id, descripcion, monto, dia_mes, categoria)
            )
            conn.commit()


def obtener_pagos_fijos(usuario_id: int) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, descripcion, monto, dia_mes, categoria FROM pagos_fijos WHERE usuario_id=%s AND activo=TRUE ORDER BY dia_mes",
                (usuario_id,)
            )
            rows = cur.fetchall()
            return rows


def eliminar_pago_fijo(pago_id: int, usuario_id: int):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE pagos_fijos SET activo=FALSE WHERE id=%s AND usuario_id=%s", (pago_id, usuario_id))
            conn.commit()


def obtener_pagos_fijos_del_dia(dia: int) -> list:
    """Retorna todos los pagos fijos de todos los usuarios para un día dado."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pf.id, pf.usuario_id, u.telegram_id, pf.descripcion, pf.monto, pf.categoria
                FROM pagos_fijos pf
                JOIN usuarios u ON u.id = pf.usuario_id
                WHERE pf.dia_mes=%s AND pf.activo=TRUE
                """,
                (dia,)
            )
            rows = cur.fetchall()
            return rows
