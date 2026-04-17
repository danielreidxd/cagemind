"""
Actualizar schema de sherdog_features.
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

DATABASE_URL = os.getenv("DATABASE_URL_NB") or os.getenv("DATABASE_URL")

ALTER_SQL = """
ALTER TABLE sherdog_features
ADD COLUMN IF NOT EXISTS pre_ufc_wins INTEGER,
ADD COLUMN IF NOT EXISTS pre_ufc_losses INTEGER,
ADD COLUMN IF NOT EXISTS pre_ufc_draws INTEGER,
ADD COLUMN IF NOT EXISTS pre_ufc_avg_finish_round REAL,
ADD COLUMN IF NOT EXISTS ufc_fights_sherdog INTEGER;
"""


def main():
    print("\nUpdating sherdog_features schema...")

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(ALTER_SQL)
        conn.commit()

        print("\nColumns added:")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'sherdog_features'
            ORDER BY ordinal_position
        """)

        for col_name, data_type in cursor.fetchall():
            print(f"  ✓ {col_name}: {data_type}")

        cursor.close()
        conn.close()
        print("\n✅ Schema updated")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)


if __name__ == "__main__":
    main()
