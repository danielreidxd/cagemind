"""
Migración completa de SQLite a PostgreSQL/Supabase.
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

ALL_TABLES = [
    "organizations",
    "fighters",
    "events",
    "fights",
    "fight_stats",
    "data_quality",
    "users",
    "analytics_events",
    "update_logs",
    "picks",
    "sherdog_features",
]


def get_sqlite_connection():
    if not SQLITE_DB_PATH.exists():
        raise FileNotFoundError(f"SQLite DB not found: {SQLITE_DB_PATH}")
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_postgres_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured in .env")
    return psycopg2.connect(DATABASE_URL)


def migrate_table(sqlite_conn, postgres_conn, table_name):
    print(f"\nMigrating table: {table_name}")

    sqlite_cursor = sqlite_conn.cursor()
    try:
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  ⚠ Table {table_name} does not exist in SQLite: {e}")
        return 0

    if not rows:
        print(f"  ℹ Table {table_name} is empty")
        return 0

    columns = [description[0] for description in sqlite_cursor.description]
    data = [dict(zip(columns, row)) for row in rows]

    boolean_columns = {
        'fighters': ['has_belt'],
        'fights': ['is_draw', 'is_no_contest'],
        'data_quality': ['has_round_stats', 'has_sig_strikes'],
        'users': ['verified'],
    }

    if table_name in boolean_columns:
        for row in data:
            for col in boolean_columns[table_name]:
                if col in row and row[col] is not None:
                    row[col] = bool(row[col])

    print(f"  ✓ Found {len(data)} records in SQLite")

    serial_tables = ['users', 'analytics_events', 'update_logs', 'picks', 'sherdog_features']
    if table_name in serial_tables:
        postgres_cursor_check = postgres_conn.cursor(cursor_factory=DictCursor)
        postgres_cursor_check.execute(f"SELECT COUNT(*) FROM {table_name}")
        existing_count = postgres_cursor_check.fetchone()[0]

        if existing_count > 0:
            seq_name = f"{table_name}_id_seq"
            postgres_cursor_check.execute(
                f"SELECT setval(%s, (SELECT COALESCE(MAX(id), 1) FROM {table_name}) + 1, false)",
                (seq_name,)
            )
            postgres_conn.commit()
            print(f"  ✓ Sequence {seq_name} reset")

        postgres_cursor_check.close()

    postgres_cursor = postgres_conn.cursor(cursor_factory=DictCursor)
    col_names = list(data[0].keys())
    col_str = ", ".join(col_names)
    placeholders = ", ".join(["%s"] * len(col_names))
    values = [tuple(row[col] for col in col_names) for row in data]

    main_tables = ["organizations", "fighters", "events", "fights", "fight_stats", "data_quality"]

    if table_name in main_tables:
        postgres_cursor_check = postgres_conn.cursor(cursor_factory=DictCursor)
        postgres_cursor_check.execute(f"SELECT COUNT(*) FROM {table_name}")
        existing_count = postgres_cursor_check.fetchone()[0]
        if existing_count > 0 and table_name != "fight_stats":
            print(f"  ℹ Table {table_name} already has {existing_count} records, skipping")
            postgres_conn.commit()
            postgres_cursor_check.close()
            return 0
        postgres_cursor_check.close()

    if table_name == "organizations":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (org_id) DO NOTHING"
    elif table_name == "fighters":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (fighter_id) DO NOTHING"
    elif table_name == "events":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (event_id) DO NOTHING"
    elif table_name == "fights":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (fight_id) DO NOTHING"
    elif table_name == "fight_stats":
        insert_cols = [c for c in col_names if c != 'stat_id']
        col_str = ", ".join(insert_cols)
        placeholders = ", ".join(["%s"] * len(insert_cols))
        values = [tuple(row[col] for col in insert_cols) for row in data]

        postgres_cursor_check = postgres_conn.cursor(cursor_factory=DictCursor)
        postgres_cursor_check.execute("SELECT COUNT(*) FROM fight_stats")
        existing_count = postgres_cursor_check.fetchone()[0]

        if existing_count > 0:
            print(f"  ℹ Table fight_stats already has {existing_count} records, skipping")
            postgres_conn.commit()
            return 0
        postgres_cursor_check.close()

        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"
    elif table_name == "data_quality":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (fight_id) DO NOTHING"
    elif table_name == "users":
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (username) DO NOTHING"
    elif table_name == "analytics_events":
        insert_cols = [c for c in col_names if c != 'id']
        col_str = ", ".join(insert_cols)
        placeholders = ", ".join(["%s"] * len(insert_cols))
        values = [tuple(row[col] for col in insert_cols) for row in data]
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"
    elif table_name == "update_logs":
        insert_cols = [c for c in col_names if c != 'id']
        col_str = ", ".join(insert_cols)
        placeholders = ", ".join(["%s"] * len(insert_cols))
        values = [tuple(row[col] for col in insert_cols) for row in data]
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"
    elif table_name == "picks":
        insert_cols = [c for c in col_names if c != 'id']
        col_str = ", ".join(insert_cols)
        placeholders = ", ".join(["%s"] * len(insert_cols))
        values = [tuple(row[col] for col in insert_cols) for row in data]
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (user_id, event_name, fighter_a, fighter_b) DO NOTHING"
    elif table_name == "sherdog_features":
        insert_cols = [c for c in col_names if c != 'id']
        col_str = ", ".join(insert_cols)
        placeholders = ", ".join(["%s"] * len(insert_cols))
        values = [tuple(row[col] for col in insert_cols) for row in data]
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT (name) DO NOTHING"
    else:
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"

    try:
        execute_batch(postgres_cursor, query, values, page_size=100)
        postgres_conn.commit()
        print(f"  ✅ {table_name} migrated successfully ({len(data)} records)")
        return len(data)
    except Exception as e:
        postgres_conn.rollback()
        print(f"  ❌ Error migrating {table_name}: {e}")
        raise


def verify_migration(postgres_conn):
    print("\n" + "="*60)
    print("MIGRATION VERIFICATION")
    print("="*60)

    cursor = postgres_conn.cursor()
    for table in ALL_TABLES:
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
        ("fight_stats", "stat_id"),
    ]

    for table, column in sequences:
        try:
            cursor.execute(f"SELECT COALESCE(MAX({column}), 0) FROM {table}")
            max_id = cursor.fetchone()[0]
            seq_name = f"{table}_{column}_seq"
            cursor.execute("SELECT setval(%s, %s, true)", (seq_name, max_id))
            print(f"  ✓ Sequence {seq_name} reset to {max_id}")
        except Exception as e:
            print(f"  ⚠ Error resetting sequence {table}_{column}: {e}")

    postgres_conn.commit()
    cursor.close()


def main():
    print("\n" + "="*60)
    print("MIGRATION: SQLite to PostgreSQL/Supabase")
    print("="*60)
    print(f"SQLite: {SQLITE_DB_PATH}")
    print(f"PostgreSQL: {DATABASE_URL[:30]}...")
    print(f"Tables: {len(ALL_TABLES)}")

    sqlite_conn = None
    postgres_conn = None

    try:
        print("\n[1/4] Establishing connections...")
        sqlite_conn = get_sqlite_connection()
        print("  ✓ SQLite connected")

        postgres_conn = get_postgres_connection()
        print("  ✓ PostgreSQL connected")

        print("\n[2/4] Migrating tables...")
        total_migrated = 0
        for table in ALL_TABLES:
            count = migrate_table(sqlite_conn, postgres_conn, table)
            total_migrated += count

        print(f"\n  ✓ Total migrated: {total_migrated} records")

        print("\n[3/4] Resetting sequences...")
        reset_sequences(postgres_conn)

        print("\n[4/4] Verifying migration...")
        verify_migration(postgres_conn)

        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("="*60)

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("Make sure to run this script from the project root")
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
        print("\nConnections closed")


if __name__ == "__main__":
    main()
