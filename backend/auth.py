from __future__ import annotations

import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext

from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS
from db.connection import get_db, is_postgresql, init_users_table as db_init_users_table

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
    db_init_users_table()


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


# ============================================================
# DB HELPERS (compatibles con SQLite y PostgreSQL)
# ============================================================

def _param_placeholder():
    """Retorna el placeholder correcto según el tipo de BD."""
    return "%s" if is_postgresql() else "?"


def execute_query(conn, query: str, params: tuple = ()):
    """Ejecuta una query con placeholders correctos."""
    cur = conn.cursor()
    cur.execute(query, params)
    return cur