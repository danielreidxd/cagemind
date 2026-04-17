"""
Router de autenticación: login, register, me.
Compatible con SQLite y PostgreSQL.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends

from backend.auth import pwd_context, create_token, get_current_user
from db.connection import get_db, is_postgresql
from backend.schemas import LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth")


def _p():
    """Placeholder de parámetros según el tipo de BD."""
    return "%s" if is_postgresql() else "?"


@router.post("/login")
async def login(req: LoginRequest):
    """Autenticación con username y password. Devuelve JWT."""
    conn = get_db()
    placeholder = _p()
    user = conn.execute(
        f"SELECT id, username, password, role FROM users WHERE username = {placeholder}",
        (req.username,),
    ).fetchone()
    conn.close()

    if not user or not pwd_context.verify(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_token(user["username"], user["role"])
    return {
        "token": token,
        "username": user["username"],
        "role": user["role"],
    }


@router.get("/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """Devuelve info del usuario autenticado."""
    return {"username": user["sub"], "role": user["role"]}


@router.post("/register")
async def register(req: RegisterRequest):
    """Registro público de usuarios con email único."""
    username = req.username.strip()
    email = req.email.strip().lower()

    if len(username) < 3 or len(username) > 20:
        raise HTTPException(status_code=400, detail="El usuario debe tener entre 3 y 20 caracteres")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    if not username.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="El usuario solo puede contener letras, números y guión bajo")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Email inválido")

    conn = get_db()
    placeholder = _p()
    if conn.execute(f"SELECT id FROM users WHERE username = {placeholder}", (username,)).fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Ese usuario ya existe")
    if conn.execute(f"SELECT id FROM users WHERE email = {placeholder}", (email,)).fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Ese email ya está registrado")

    hashed = pwd_context.hash(req.password)
    conn.execute(
        f"INSERT INTO users (username, email, password, role) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})",
        (username, email, hashed, "user"),
    )
    conn.commit()
    conn.close()

    token = create_token(username, "user")
    return {"token": token, "username": username, "role": "user"}