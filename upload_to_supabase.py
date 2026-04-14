import sqlite3
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Conexión Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Conexión SQLite
conn_sqlite = sqlite3.connect('db/ufc_predictor.db')
conn_sqlite.row_factory = sqlite3.Row

def migrate_table(table_name):
    print(f"Migrando {table_name}...")
    cursor = conn_sqlite.execute(f"SELECT * FROM {table_name}")
    rows = [dict(row) for row in cursor.fetchall()]
    
    if not rows:
        print(f"La tabla {table_name} está vacía.")
        return

    # Insertar en bloques para no saturar la API
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        try:
            supabase.table(table_name).upsert(batch).execute()
        except Exception as e:
            print(f"Error en batch de {table_name}: {e}")
            
    print(f"✅ {table_name} migrada.")

# Lista de tablas en orden de jerarquía (para no romper llaves foráneas)
tablas = ["organizations", "fighters", "events", "fights", "fight_stats", "data_quality"]

for t in tablas:
    migrate_table(t)

conn_sqlite.close()
print("--- PROCESO FINALIZADO ---")