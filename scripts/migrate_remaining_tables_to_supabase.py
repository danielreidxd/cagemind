"""
Migración de tablas faltantes a Supabase.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

import sqlite3
import psycopg2
from psycopg2.extras import execute_batch, DictCursor

SQLITE_DB_PATH = Path("db/ufc_predictor.db")
DATABASE_URL = os.getenv("DATABASE_URL_NB")

TABLES_TO_MIGRATE = ["users", "analytics_events", "update_logs", "picks", "sherdog_features"]


def get_sqlite_connection():
    if not SQLITE_DB_PATH.exists():
        raise FileNotFoundError(f"SQLite DB not found: {SQLITE_DB_PATH}")
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_postgres_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    return psycopg2.connect(DATABASE_URL)


def migrate_table(sqlite_conn, postgres_conn, table_name):
    print(f"\nMigrating {table_name}...")

    sqlite_cursor = sqlite_conn.cursor()
    try:
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  ⚠ Table {table_name} does not exist: {e}")
        return 0

    if not rows:
        print(f"  ℹ Table {table_name} is empty")
        return 0

    columns = [description[0] for description in sqlite_cursor.description]
    data = [dict(zip(columns, row)) for row in rows]

    boolean_columns = {'users': ['verified']}
    if table_name in boolean_columns:
        for row in data:
            for col in boolean_columns[table_name]:
                if col in row and row[col] is not None:
                    row[col] = bool(row[col])

    print(f"  ✓ Found {len(data)} records")

    postgres_cursor = postgres_conn.cursor(cursor_factory=DictCursor)
    col_names = list(data[0].keys())
    col_str = ", ".join(col_names)
    placeholders = ", ".join(["%s"] * len(col_names))
    values = [tuple(row[col] for col in col_names) for row in data]

    if table_name == "users":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (username) DO UPDATE SET email = EXCLUDED.email, password = EXCLUDED.password, role = EXCLUDED.role, verified = EXCLUDED.verified, updated_at = CURRENT_TIMESTAMP"
    elif table_name == "picks":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (user_id, event_name, fighter_a, fighter_b) DO UPDATE SET picked_winner = EXCLUDED.picked_winner, created_at = EXCLUDED.created_at"
    elif table_name == "sherdog_features":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (name) DO UPDATE SET pre_ufc_fights = EXCLUDED.pre_ufc_fights, pre_ufc_wr = EXCLUDED.pre_ufc_wr, updated_at = CURRENT_TIMESTAMP"
    else:
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"

    try:
        execute_batch(postgres_cursor, query, values, page_size=100)
        postgres_conn.commit()
        print(f"  ✅ {table_name} migrated ({len(data)} records)")
        return len(data)
    except Exception as e:
        postgres_conn.rollback()
        print(f"  ❌ Error: {e}")
        raise


def verify_migration(postgres_conn):
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)

    cursor = postgres_conn.cursor()
    for table in TABLES_TO_MIGRATE:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table}: {count} records")
        except Exception as e:
            print(f"  ✗ {table}: Error - {e}")
    cursor.close()


def reset_sequences(postgres_conn):
    print("\n" + "="*60)
    print("RESETTING SEQUENCES")
    print("="*60)

    cursor = postgres_conn.cursor()
    sequences = [
        ("users", "id"),
        ("analytics_events", "id"),
        ("update_logs", "id"),
        ("picks", "id"),
        ("sherdog_features", "id"),
    ]

    for table, column in sequences:
        try:
            cursor.execute(f"SELECT COALESCE(MAX({column}), 0) FROM {table}")
            max_id = cursor.fetchone()[0]
            seq_name = f"{table}_{column}_seq"
            cursor.execute("SELECT setval(%s, %s, true)", (seq_name, max_id))
            print(f"  ✓ {seq_name} reset to {max_id}")
        except Exception as e:
            print(f"  ⚠ Error with {seq_name}: {e}")

    postgres_conn.commit()
    cursor.close()


def main():
    print("\n" + "="*60)
    print("MIGRATION: Remaining Tables to Supabase")
    print("="*60)

    sqlite_conn = None
    postgres_conn = None

    try:
        print("\n[1/4] Connecting...")
        sqlite_conn = get_sqlite_connection()
        postgres_conn = get_postgres_connection()
        print("  ✓ Connected")

        print("\n[2/4] Migrating tables...")
        total = 0
        for table in TABLES_TO_MIGRATE:
            count = migrate_table(sqlite_conn, postgres_conn, table)
            total += count
        print(f"\n  ✓ Total: {total} records migrated")

        print("\n[3/4] Resetting sequences...")
        reset_sequences(postgres_conn)

        print("\n[4/4] Verifying...")
        verify_migration(postgres_conn)

        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED")
        print("="*60)

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if sqlite_conn:
            sqlite_conn.close()
        if postgres_conn:
            postgres_conn.close()


if __name__ == "__main__":
    main()
