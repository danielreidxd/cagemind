"""
Funciones helper para compatibilidad entre SQLite y PostgreSQL.
Maneja las diferencias de sintaxis SQL entre ambas bases de datos.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def is_postgresql():
    """Retorna True si DATABASE_URL indica PostgreSQL."""
    database_url = os.environ.get("DATABASE_URL", "")
    return database_url.startswith("postgresql")


def get_db_url():
    """Retorna la URL de base de datos desde variables de entorno."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        db_path = Path("db/ufc_predictor.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"
    return url


def param():
    """Retorna el placeholder de parámetro según el tipo de BD."""
    return "%s" if is_postgresql() else "?"


def params(n):
    """Retorna n placeholders separados por coma."""
    p = param()
    return ", ".join([p] * n)


def insert_or_ignore(table, columns, values):
    """
    Genera una sentencia INSERT OR IGNORE (SQLite) o INSERT ... ON CONFLICT DO NOTHING (PostgreSQL).
    Retorna (query, values_tuple)
    """
    if is_postgresql():
        col_str = ", ".join(columns)
        val_str = ", ".join(["%s"] * len(columns))
        # Para PostgreSQL, necesitamos saber la constraint de UNIQUE
        # Usamos la primera columna como clave de conflicto
        pk_col = columns[0] if columns else "id"
        query = f"INSERT INTO {table} ({col_str}) VALUES ({val_str}) ON CONFLICT ({pk_col}) DO NOTHING"
    else:
        col_str = ", ".join(columns)
        val_str = ", ".join(["?"] * len(columns))
        query = f"INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({val_str})"
    return query, values


def insert_or_replace(table, columns, values):
    """
    Genera una sentencia INSERT OR REPLACE (SQLite) o INSERT ... ON CONFLICT DO UPDATE (PostgreSQL).
    Retorna (query, values_tuple)
    """
    if is_postgresql():
        col_str = ", ".join(columns)
        val_str = ", ".join(["%s"] * len(columns))
        pk_col = columns[0] if columns else "id"
        update_cols = [c for c in columns if c != pk_col]
        if update_cols:
            update_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
            query = f"INSERT INTO {table} ({col_str}) VALUES ({val_str}) ON CONFLICT ({pk_col}) DO UPDATE SET {update_str}"
        else:
            query = f"INSERT INTO {table} ({col_str}) VALUES ({val_str}) ON CONFLICT ({pk_col}) DO NOTHING"
    else:
        col_str = ", ".join(columns)
        val_str = ", ".join(["?"] * len(columns))
        query = f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({val_str})"
    return query, values


def coalesce(val, fallback_col):
    """
    Retorna la sintaxis COALESCE correcta.
    En SQLite: COALESCE(?, col_name)
    En PostgreSQL: COALESCE(%s, col_name)
    """
    p = param()
    return f"COALESCE({p}, {fallback_col})"