"""
Módulo de conexión a base de datos compatible con SQLite y PostgreSQL.
Usa la variable de entorno DATABASE_URL para determinar el tipo de conexión.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from contextlib import contextmanager

# Agregar el directorio raíz del proyecto al path para imports relativos
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_db():
    """
    Retorna una conexión compatible con SQLite o PostgreSQL según DATABASE_URL.
    - Si DATABASE_URL empieza con "postgresql", usa psycopg2
    - Si DATABASE_URL empieza con "sqlite", usa sqlite3
    """
    database_url = os.environ.get("DATABASE_URL", "")
    
    if not database_url:
        # Fallback a SQLite local
        db_path = Path("db/ufc_predictor.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{db_path}"
    
    if database_url.startswith("postgresql"):
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(database_url)
        conn.cursor_factory = psycopg2.extras.DictCursor
        return conn
    else:
        import sqlite3
        clean_path = database_url.replace("sqlite:///", "")
        conn = sqlite3.connect(clean_path)
        conn.row_factory = sqlite3.Row
        return conn


def get_cursor(conn):
    """
    Retorna un cursor compatible con SQLite o PostgreSQL.
    Para PostgreSQL, usa DictCursor para acceso por nombre de columna.
    """
    database_url = os.environ.get("DATABASE_URL", "")
    
    if database_url.startswith("postgresql"):
        import psycopg2.extras
        return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    else:
        return conn.cursor()


@contextmanager
def get_db_context():
    """
    Context manager para conexión a base de datos.
    Asegura que la conexión se cierre correctamente.
    """
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row):
    """
    Convierte una fila a diccionario, compatible con ambos drivers.
    """
    if row is None:
        return None
    if hasattr(row, "keys"):
        # psycopg2.extras.DictRow o sqlite3.Row
        return dict(row)
    # Fallback para tuplas simples
    return row


def is_postgresql():
    """Retorna True si se está usando PostgreSQL."""
    database_url = os.environ.get("DATABASE_URL", "")
    return database_url.startswith("postgresql")


def init_users_table(conn=None):
    """
    Crea las tablas de usuarios si no existen.
    Compatible con SQLite y PostgreSQL.
    """
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True
    
    try:
        if is_postgresql():
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            cur = conn.cursor()
        
        # Tabla users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          SERIAL PRIMARY KEY,
                username    TEXT NOT NULL UNIQUE,
                email       TEXT UNIQUE,
                password    TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'user',
                verified    BOOLEAN DEFAULT FALSE,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla analytics_events
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id          SERIAL PRIMARY KEY,
                event_type  TEXT NOT NULL,
                page        TEXT,
                detail      TEXT,
                ip          TEXT,
                user_agent  TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla update_logs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS update_logs (
                id          SERIAL PRIMARY KEY,
                action      TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'running',
                result      TEXT,
                started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            )
        """)
        
        # Tabla picks
        cur.execute("""
            CREATE TABLE IF NOT EXISTS picks (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER NOT NULL,
                event_name      TEXT NOT NULL,
                fighter_a       TEXT NOT NULL,
                fighter_b       TEXT NOT NULL,
                picked_winner   TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, event_name, fighter_a, fighter_b)
            )
        """)
        
        # Índice para email (PostgreSQL usa IF NOT EXISTS)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)
        
        conn.commit()

        # Crear admin si no existe
        p = "%s" if is_postgresql() else "?"
        cur.execute(f"SELECT id FROM users WHERE username = {p}", ("admin",))
        existing = cur.fetchone()

        if not existing:
            import os
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            admin_pass = os.environ.get("ADMIN_PASSWORD", "cagemind2026")
            hashed = pwd_context.hash(admin_pass)
            
            if is_postgresql():
                cur.execute(
                    "INSERT INTO users (username, password, role) VALUES (%s, %s, %s) RETURNING id",
                    ("admin", hashed, "admin"),
                )
                admin_id = cur.fetchone()[0]
            else:
                cur.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("admin", hashed, "admin"),
                )
                admin_id = cur.lastrowid
            
            conn.commit()
            print(f"Usuario admin creado (id: {admin_id}, password: {'***' if 'ADMIN_PASSWORD' in os.environ else admin_pass})")

        cur.close()
    finally:
        if should_close:
            conn.close()