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
                cur.execute("INSERT INTO cuentas (usuario_id, nombre, saldo_inicial, es_principal) VALUES (%s, 'Principal', 0, TRUE)", (usuario_id,))
                conn.commit()
            else:
                usuario_id = usuario[0]
            return usuario_id

# ── Cuentas ──────────────────────────────────────────────────────────────────

def obtener_cuentas(usuario_id: int, solo_activas: bool = True) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT id, nombre, saldo_inicial, es_principal, activa FROM cuentas WHERE usuario_id=%s"
            if solo_activas:
                query += " AND activa=TRUE"
            query += " ORDER BY id"
            cur.execute(query, (usuario_id,))
            return cur.fetchall()

def obtener_cuenta_principal(usuario_id: int):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM cuentas WHERE usuario_id=%s AND es_principal=TRUE", (usuario_id,))
            res = cur.fetchone()
            return res[0] if res else None

def obtener_cuenta_por_nombre(usuario_id: int, nombre: str):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM cuentas WHERE usuario_id=%s AND activa=TRUE AND LOWER(nombre)=LOWER(%s)", (usuario_id, nombre))
            res = cur.fetchone()
            return res[0] if res else None

def crear_cuenta(usuario_id: int, nombre: str, saldo_inicial: float = 0):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO cuentas (usuario_id, nombre, saldo_inicial) VALUES (%s, %s, %s)", (usuario_id, nombre, saldo_inicial))
            conn.commit()

def archivar_cuenta(usuario_id: int, cuenta_id: int):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE cuentas SET activa=FALSE WHERE id=%s AND usuario_id=%s AND es_principal=FALSE", (cuenta_id, usuario_id))
            conn.commit()
            
def ajustar_saldo_inicial(usuario_id: int, cuenta_id: int, nuevo_saldo: float):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE cuentas SET saldo_inicial=%s WHERE id=%s AND usuario_id=%s", (nuevo_saldo, cuenta_id, usuario_id))
            conn.commit()


def registrar_transferencia(usuario_id: int, cuenta_origen_id: int, cuenta_destino_id: int, monto: float, descripcion: str, fecha=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            # Gasto en cuenta origen
            query_origen = "INSERT INTO transacciones (usuario_id, monto, medio, descripcion, categoria, cuenta_id"
            vals_origen = [usuario_id, monto, "Transferencia Interna", descripcion, "Transferencia", cuenta_origen_id]
            if fecha:
                query_origen += ", fecha) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                vals_origen.append(fecha)
            else:
                query_origen += ") VALUES (%s, %s, %s, %s, %s, %s)"
            cur.execute(query_origen, tuple(vals_origen))
            
            # Ingreso en cuenta destino
            query_destino = "INSERT INTO ingresos (usuario_id, monto, descripcion, categoria, cuenta_id"
            vals_destino = [usuario_id, monto, descripcion, "Transferencia", cuenta_destino_id]
            if fecha:
                query_destino += ", fecha) VALUES (%s, %s, %s, %s, %s, %s)"
                vals_destino.append(fecha)
            else:
                query_destino += ") VALUES (%s, %s, %s, %s, %s)"
            cur.execute(query_destino, tuple(vals_destino))
            
            conn.commit()



def guardar_transaccion(usuario_id, monto, medio, descripcion, categoria, destinatario="No detectado", fecha_voucher="No detectada", fecha=None, cuenta_id=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            if cuenta_id is None:
                cur.execute("SELECT id FROM cuentas WHERE usuario_id=%s AND es_principal=TRUE", (usuario_id,))
                res = cur.fetchone()
                cuenta_id = res[0] if res else None

            if fecha:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha, cuenta_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha, cuenta_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, cuenta_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, cuenta_id),
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

def actualizar_medio_transaccion(trans_id: int, usuario_id: int, medio: str):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE transacciones SET medio=%s WHERE id=%s AND usuario_id=%s",
                (medio, trans_id, usuario_id)
            )
            conn.commit()


def obtener_total_mes(usuario_id: int, cuenta_id=None) -> float:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT COALESCE(SUM(monto::numeric), 0)
                FROM transacciones
                WHERE usuario_id=%s
                  AND date_trunc('month', fecha) = date_trunc('month', NOW())
                """
            params = [usuario_id]
            if cuenta_id is not None:
                query += " AND cuenta_id=%s"
                params.append(cuenta_id)
            else:
                query += " AND categoria != 'Transferencia'"
                
            cur.execute(query, tuple(params))
            total = cur.fetchone()[0]
            return float(total)


def obtener_historial(usuario_id: int, limite: int = 10, offset: int = 0) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT monto, medio, descripcion, categoria, destinatario, fecha
                FROM transacciones
                WHERE usuario_id=%s
                ORDER BY fecha DESC
                LIMIT %s OFFSET %s
                """,
                (usuario_id, limite, offset),
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
                  AND categoria != 'Transferencia'
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

def guardar_ingreso(usuario_id: int, monto: float, descripcion: str, categoria: str = "Ingreso", cuenta_id=None, fecha=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            if cuenta_id is None:
                cur.execute("SELECT id FROM cuentas WHERE usuario_id=%s AND es_principal=TRUE", (usuario_id,))
                res = cur.fetchone()
                cuenta_id = res[0] if res else None

            query = "INSERT INTO ingresos (usuario_id, monto, descripcion, categoria, cuenta_id"
            vals = [usuario_id, monto, descripcion, categoria, cuenta_id]
            
            if fecha:
                query += ", fecha) VALUES (%s, %s, %s, %s, %s, %s)"
                vals.append(fecha)
            else:
                query += ") VALUES (%s, %s, %s, %s, %s)"

            cur.execute(query, tuple(vals))
            conn.commit()

def actualizar_medio_ingreso_reciente(usuario_id: int, medio: str):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE ingresos SET descripcion = descripcion || ' (' || %s || ')'
                   WHERE usuario_id=%s AND fecha >= NOW() - INTERVAL '5 minutes'
                   AND descripcion NOT LIKE '%%(%%)' """,
                (medio, usuario_id)
            )
            conn.commit()


def obtener_total_ingresos_mes(usuario_id: int, cuenta_id=None) -> float:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT COALESCE(SUM(monto), 0) FROM ingresos
                WHERE usuario_id=%s AND date_trunc('month', fecha) = date_trunc('month', NOW())
                """
            params = [usuario_id]
            if cuenta_id is not None:
                query += " AND cuenta_id=%s"
                params.append(cuenta_id)
            else:
                query += " AND categoria != 'Transferencia'"
                
            cur.execute(query, tuple(params))
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

def obtener_ultimas_transacciones(usuario_id: int, limite: int = 5, offset: int = 0) -> list:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, monto, descripcion, categoria, medio, fecha
                FROM transacciones WHERE usuario_id=%s
                ORDER BY fecha DESC LIMIT %s OFFSET %s
                """,
                (usuario_id, limite, offset)
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

def guardar_pago_fijo(usuario_id: int, descripcion: str, monto: float, dia_mes: int, categoria: str = "Servicios", cuenta_id=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            if cuenta_id is None:
                cur.execute("SELECT id FROM cuentas WHERE usuario_id=%s AND es_principal=TRUE", (usuario_id,))
                res = cur.fetchone()
                cuenta_id = res[0] if res else None
                
            cur.execute(
                "INSERT INTO pagos_fijos (usuario_id, descripcion, monto, dia_mes, categoria, cuenta_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (usuario_id, descripcion, monto, dia_mes, categoria, cuenta_id)
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
