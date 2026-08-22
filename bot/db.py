"""
db.py — FinanzasBot v2.5
Agrega funciones para historial, resumen por categoría y exportar.
"""

from psycopg_pool import ConnectionPool
from config import DB_CONFIG

db_pool = ConnectionPool(conninfo=DB_CONFIG)

# Categorías que mueven el saldo pero no son ingreso ni gasto: una transferencia
# cambia la plata de cuenta y un préstamo la cambia de manos, no de dueño.
# Debe coincidir con panel-web/backend/app/core/constantes.py
CATEGORIAS_SIN_TOTALES = ("Transferencia", "Prestamo")

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

# ── Categorías ───────────────────────────────────────────────────────────────

def obtener_categorias(usuario_id: int, tipo: str) -> list:
    """Nombres que el usuario puede usar: las de sistema más las propias.

    Excluye tipo 'ambos' (Transferencia): no se clasifica, se deduce del flujo.
    """
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT nombre FROM categorias "
                "WHERE (usuario_id IS NULL OR usuario_id=%s) AND activa AND tipo=%s "
                "ORDER BY es_sistema DESC, nombre",
                (usuario_id, tipo),
            )
            return [fila[0] for fila in cur.fetchall()]


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



def guardar_transaccion(usuario_id, monto, medio, descripcion, categoria, destinatario="No detectado", fecha_voucher="No detectada", fecha=None, cuenta_id=None) -> int:
    """Devuelve el id de la transacción insertada."""
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
                    RETURNING id
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha, cuenta_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, cuenta_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, cuenta_id),
                )
            transaccion_id = cur.fetchone()[0]
            conn.commit()
            return transaccion_id


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

def actualizar_medio_transacciones(usuario_id: int, trans_ids, medio: str) -> int:
    """Fija el medio de transacciones concretas y devuelve cuántas filas tocó.

    Reemplaza a `actualizar_medio_ultimas` en los flujos que ya conocen los ids
    que acaban de insertar: la ventana de "los últimos 5 minutos" no alcanzaba
    ningún gasto con fecha de ayer ni ninguna fila importada de un historial,
    así que la respuesta del usuario se perdía en silencio.

    El id nunca se usa solo: siempre va acotado al usuario_id.
    """
    ids = [int(i) for i in (trans_ids or [])]
    if not ids:
        return 0
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE transacciones SET medio=%s WHERE usuario_id=%s AND id = ANY(%s)",
                (medio, usuario_id, ids),
            )
            filas = cur.rowcount
            conn.commit()
            return filas


def actualizar_medio_transaccion(trans_id: int, usuario_id: int, medio: str):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE transacciones SET medio=%s WHERE id=%s AND usuario_id=%s",
                (medio, trans_id, usuario_id)
            )
            conn.commit()


def obtener_tendencia_gastos(usuario_id: int) -> dict:
    from datetime import datetime
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            hoy = datetime.now()
            mes_actual = hoy.month
            anio_actual = hoy.year
            dia_actual = hoy.day
            
            if mes_actual == 1:
                mes_pasado = 12
                anio_pasado = anio_actual - 1
            else:
                mes_pasado = mes_actual - 1
                anio_pasado = anio_actual

            # Gasto actual hasta hoy
            cur.execute("""
                SELECT COALESCE(SUM(monto::numeric), 0) FROM transacciones 
                WHERE usuario_id=%s AND EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s
                AND EXTRACT(DAY FROM fecha) <= %s AND categoria NOT IN ('Transferencia', 'Prestamo')
            """, (usuario_id, anio_actual, mes_actual, dia_actual))
            gasto_actual = cur.fetchone()[0]

            # Gasto mes pasado hasta el mismo día
            cur.execute("""
                SELECT COALESCE(SUM(monto::numeric), 0) FROM transacciones 
                WHERE usuario_id=%s AND EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s
                AND EXTRACT(DAY FROM fecha) <= %s AND categoria NOT IN ('Transferencia', 'Prestamo')
            """, (usuario_id, anio_pasado, mes_pasado, dia_actual))
            gasto_pasado = cur.fetchone()[0]

            # Desglose semanal del mes actual
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN EXTRACT(DAY FROM fecha) <= 7 THEN 1
                        WHEN EXTRACT(DAY FROM fecha) <= 14 THEN 2
                        WHEN EXTRACT(DAY FROM fecha) <= 21 THEN 3
                        ELSE 4
                    END as semana,
                    COALESCE(SUM(monto::numeric), 0)
                FROM transacciones
                WHERE usuario_id=%s AND EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s
                AND categoria NOT IN ('Transferencia', 'Prestamo')
                GROUP BY semana
                ORDER BY semana
            """, (usuario_id, anio_actual, mes_actual))
            
            semanas = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
            for row in cur.fetchall():
                semanas[int(row[0])] = float(row[1])

            return {
                "gasto_actual": float(gasto_actual),
                "gasto_pasado": float(gasto_pasado),
                "semanas": semanas,
                "dia_actual": dia_actual
            }

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
                query += " AND categoria NOT IN ('Transferencia', 'Prestamo')"
                
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
                  AND categoria NOT IN ('Transferencia', 'Prestamo')
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

def guardar_ingreso(usuario_id: int, monto: float, descripcion: str, categoria: str = "Otros ingresos", cuenta_id=None, fecha=None):
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
                query += " AND categoria NOT IN ('Transferencia', 'Prestamo')"
                
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
                SELECT id, monto, descripcion, categoria, medio, fecha, 'gasto' as tipo
                FROM transacciones WHERE usuario_id=%s
                UNION ALL
                SELECT id, monto, descripcion, categoria, NULL as medio, fecha, 'ingreso' as tipo
                FROM ingresos WHERE usuario_id=%s
                ORDER BY fecha DESC LIMIT %s OFFSET %s
                """,
                (usuario_id, usuario_id, limite, offset)
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

def eliminar_ingreso(ingreso_id: int, usuario_id: int) -> bool:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM ingresos WHERE id=%s AND usuario_id=%s",
                (ingreso_id, usuario_id)
            )
            eliminado = cur.rowcount > 0
            conn.commit()
            return eliminado

def editar_ingreso(ingreso_id: int, usuario_id: int, monto: float, descripcion: str, categoria: str):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ingresos SET monto=%s, descripcion=%s, categoria=%s
                WHERE id=%s AND usuario_id=%s
                """,
                (monto, descripcion, categoria, ingreso_id, usuario_id)
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


# ── Vinculación con el panel web ─────────────────────────────────────────────

def crear_codigo_vinculacion(usuario_id: int, ttl_minutos: int = 10) -> str:
    """Genera un código de un solo uso para vincular la cuenta web.

    En BD solo queda el SHA-256; el código en claro se muestra una vez por chat.
    Invalida los códigos previos del usuario que sigan vigentes.
    """
    import hashlib
    import secrets

    alfabeto = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sin caracteres ambiguos
    codigo = "".join(secrets.choice(alfabeto) for _ in range(8))
    codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()

    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE codigos_vinculacion SET usado=TRUE "
                "WHERE usuario_id=%s AND usado=FALSE AND expira_en > NOW()",
                (usuario_id,),
            )
            cur.execute(
                "INSERT INTO codigos_vinculacion (usuario_id, codigo_hash, expira_en) "
                "VALUES (%s, %s, NOW() + make_interval(mins => %s))",
                (usuario_id, codigo_hash, ttl_minutos),
            )
            conn.commit()
    return codigo


def obtener_vinculo_web(usuario_id: int):
    """Devuelve (auth_uid, creado_en) si la cuenta ya está vinculada, o None."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT auth_uid, creado_en FROM vinculos_auth WHERE usuario_id=%s",
                (usuario_id,),
            )
            return cur.fetchone()


def desvincular_web(usuario_id: int) -> bool:
    """Elimina el vínculo con la cuenta web. True si había uno."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM vinculos_auth WHERE usuario_id=%s", (usuario_id,))
            borrados = cur.rowcount
            conn.commit()
            return borrados > 0


def obtener_montos_fecha_rango(usuario_id: int, desde: str, hasta: str) -> list[tuple]:
    """(monto, fecha 'YYYY-MM-DD') de gastos e ingresos del usuario en el rango.

    Se compara contra las dos tablas, no solo gastos: si ya existe un ingreso con
    ese mismo monto y fecha, también vale la pena que el checklist lo marque
    como sospechoso — es al usuario a quien le toca decidir si es coincidencia.
    """
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT monto::numeric, to_char(fecha, 'YYYY-MM-DD') AS f
                FROM transacciones
                WHERE usuario_id=%s AND fecha::date BETWEEN %s AND %s
                UNION ALL
                SELECT monto::numeric, to_char(fecha, 'YYYY-MM-DD') AS f
                FROM ingresos
                WHERE usuario_id=%s AND fecha::date BETWEEN %s AND %s
                """,
                (usuario_id, desde, hasta, usuario_id, desde, hasta),
            )
            return [(float(m), f) for m, f in cur.fetchall()]
