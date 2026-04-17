"""
Verificar conexión y estado de Supabase.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

import psycopg2
from psycopg2.extras import DictCursor

DATABASE_URL = os.getenv("DATABASE_URL_NB") or os.getenv("DATABASE_URL")

EXPECTED_TABLES = [
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


def main():
    print("\n" + "="*60)
    print("SUPABASE CONNECTION VERIFICATION")
    print("="*60)

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("✓ Connection successful")

        cursor = conn.cursor(cursor_factory=DictCursor)

        print("\n" + "="*60)
        print("TABLES")
        print("="*60)

        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in EXPECTED_TABLES:
            status = "✓" if table in existing_tables else "✗"
            print(f"  {status} {table}")

        print("\n" + "="*60)
        print("RECORD COUNTS")
        print("="*60)

        for table in EXPECTED_TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✓ {table}: {count} records")
            except Exception as e:
                print(f"  ✗ {table}: Error - {e}")

        print("\n" + "="*60)
        print("ADMIN USER")
        print("="*60)

        cursor.execute("""
            SELECT id, username, email, role, created_at
            FROM users WHERE username = 'admin'
        """)
        admin = cursor.fetchone()

        if admin:
            print(f"  ✓ Admin user found")
            print(f"    ID: {admin['id']}")
            print(f"    Email: {admin['email'] or 'N/A'}")
            print(f"    Role: {admin['role']}")
        else:
            print("  ⚠ Admin user not found")

        cursor.close()
        conn.close()

        print("\n" + "="*60)
        print("✅ VERIFICATION COMPLETED")
        print("="*60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        if conn:
            conn.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
