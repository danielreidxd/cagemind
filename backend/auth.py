
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext

from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS
from backend.database import get_db

# ============================================================
# SEGURIDAD
# ============================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# ============================================================
# INIT TABLES
# ============================================================

def init_users_table():
    """Crea las tablas users, analytics, update_logs, y picks si no existen."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL UNIQUE,
            email       TEXT UNIQUE,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'user',
            verified    BOOLEAN DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migración: agregar columna email si no existe (para DBs creadas antes de v1.1)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    conn.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            page        TEXT,
            detail      TEXT,
            ip          TEXT,
            user_agent  TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS update_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            action      TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'running',
            result      TEXT,
            started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS picks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            event_name      TEXT NOT NULL,
            fighter_a       TEXT NOT NULL,
            fighter_b       TEXT NOT NULL,
            picked_winner   TEXT NOT NULL,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, event_name, fighter_a, fighter_b)
        )
    """)

    conn.commit()

    # Crear admin si no existe
    existing = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if not existing:
        admin_pass = os.environ.get("ADMIN_PASSWORD", "cagemind2026")
        hashed = pwd_context.hash(admin_pass)
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", hashed, "admin"),
        )
        conn.commit()
        print(f"Usuario admin creado (password: {'***' if 'ADMIN_PASSWORD' in os.environ else admin_pass})")

    conn.close()


# ============================================================
# TOKEN HELPERS
# ============================================================

def create_token(username: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "role": role, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


# ============================================================
# DEPENDENCIAS DE INYECCIÓN (FastAPI Depends)
# ============================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="No autenticado")
    return verify_token(credentials.credentials)


async def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    return user
