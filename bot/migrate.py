import psycopg
from config import DB_CONFIG

def main():
    print("Iniciando migración de base de datos...")
    with psycopg.connect(DB_CONFIG) as conn:
        with conn.cursor() as cur:
            # 1. Crear tabla cuentas
            print("1. Creando tabla cuentas...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cuentas (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER REFERENCES usuarios(id),
                    nombre TEXT NOT NULL,
                    saldo_inicial NUMERIC DEFAULT 0,
                    es_principal BOOLEAN DEFAULT FALSE,
                    activa BOOLEAN DEFAULT TRUE
                );
            """)

            # 2. Insertar cuenta principal para cada usuario existente
            print("2. Creando cuentas 'Principal' para usuarios...")
            cur.execute("""
                INSERT INTO cuentas (usuario_id, nombre, saldo_inicial, es_principal)
                SELECT id, 'Principal', 0, TRUE FROM usuarios
                WHERE id NOT IN (SELECT usuario_id FROM cuentas WHERE es_principal = TRUE);
            """)

            # 3. Alterar tablas existentes
            print("3. Añadiendo cuenta_id a transacciones, ingresos y pagos_fijos...")
            for table in ["transacciones", "ingresos", "pagos_fijos"]:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES cuentas(id);")

            # 4. Actualizar registros antiguos
            print("4. Actualizando registros...")
            cur.execute("""
                UPDATE transacciones t
                SET cuenta_id = c.id
                FROM cuentas c
                WHERE c.usuario_id = t.usuario_id AND c.es_principal = TRUE AND t.cuenta_id IS NULL;
            """)
            cur.execute("""
                UPDATE ingresos i
                SET cuenta_id = c.id
                FROM cuentas c
                WHERE c.usuario_id = i.usuario_id AND c.es_principal = TRUE AND i.cuenta_id IS NULL;
            """)
            cur.execute("""
                UPDATE pagos_fijos p
                SET cuenta_id = c.id
                FROM cuentas c
                WHERE c.usuario_id = p.usuario_id AND c.es_principal = TRUE AND p.cuenta_id IS NULL;
            """)

            conn.commit()
            print("Migración completada con éxito.")

if __name__ == '__main__':
    main()
