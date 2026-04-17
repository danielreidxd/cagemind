"""
Crear tablas faltantes en Supabase.
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

TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS analytics_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    page VARCHAR(255),
    detail TEXT,
    ip VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics_events(created_at);

CREATE TABLE IF NOT EXISTS update_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    result TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_update_logs_action ON update_logs(action);
CREATE INDEX IF NOT EXISTS idx_update_logs_started_at ON update_logs(started_at);

CREATE TABLE IF NOT EXISTS picks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    fighter_a VARCHAR(255) NOT NULL,
    fighter_b VARCHAR(255) NOT NULL,
    picked_winner VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_picks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uniq_picks UNIQUE (user_id, event_name, fighter_a, fighter_b)
);

CREATE INDEX IF NOT EXISTS idx_picks_user_id ON picks(user_id);
CREATE INDEX IF NOT EXISTS idx_picks_event_name ON picks(event_name);

CREATE TABLE IF NOT EXISTS sherdog_features (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    pre_ufc_fights INTEGER,
    pre_ufc_wins INTEGER,
    pre_ufc_losses INTEGER,
    pre_ufc_draws INTEGER,
    pre_ufc_wr REAL,
    pre_ufc_ko_rate REAL,
    pre_ufc_sub_rate REAL,
    pre_ufc_dec_rate REAL,
    pre_ufc_finish_rate REAL,
    pre_ufc_ko_loss_rate REAL,
    pre_ufc_sub_loss_rate REAL,
    pre_ufc_avg_finish_round REAL,
    pre_ufc_streak INTEGER,
    total_pro_fights INTEGER,
    org_level INTEGER,
    ufc_fights_sherdog INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sherdog_features_name ON sherdog_features(name);
"""


def main():
    print("\nCreating missing tables in Supabase...")

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(TABLES_SQL)
        conn.commit()

        print("\nTables created:")
        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename IN ('users', 'analytics_events', 'update_logs', 'picks', 'sherdog_features')
            ORDER BY tablename
        """)

        tables = [row[0] for row in cursor.fetchall()]
        for table in ['users', 'analytics_events', 'update_logs', 'picks', 'sherdog_features']:
            status = "✓" if table in tables else "✗"
            print(f"  {status} {table}")

        cursor.close()
        conn.close()

        print("\n✅ Tables created successfully")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)


if __name__ == "__main__":
    main()
