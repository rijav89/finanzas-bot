import psycopg
from config import DB_CONFIG

def main():
    with psycopg.connect(DB_CONFIG) as conn:
        with conn.cursor() as cur:
            tables = ['usuarios', 'transacciones', 'ingresos', 'pagos_fijos']
            for table in tables:
                print(f"Table: {table}")
                try:
                    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}';")
                    for col in cur.fetchall():
                        print(f"  - {col[0]}: {col[1]}")
                except Exception as e:
                    print(f"Error checking table {table}: {e}")

if __name__ == '__main__':
    main()
