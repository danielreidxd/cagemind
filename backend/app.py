"""
UFC Fight Predictor — API Backend (FastAPI)

Endpoints:
  GET  /                        → Health check
  GET  /fighters                → Lista de peleadores (con búsqueda)
  GET  /fighters/{name}         → Perfil detallado de un peleador
  POST /predict                 → Predicción de pelea (Sandbox)
  GET  /upcoming                → Peleas próximas con predicciones (placeholder)
  GET  /stats                   → Estadísticas generales de la BD

Uso:
    cd ufc-fight-predictor
    python -m pip install fastapi uvicorn[standard]
    python -m uvicorn backend.app:app --reload --port 8000

Docs automáticas: http://localhost:8000/docs
"""
from __future__ import annotations

import os
import pickle
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext

# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_PATH = Path("db/ufc_predictor.db")
MODELS_PATH = Path("ml/models/ufc_predictor_models.pkl")
FEATURES_PATH = Path("ml/models/feature_names.json")

app = FastAPI(
    title="UFC Fight Predictor API",
    description="API de predicción de peleas UFC basada en Machine Learning",
    version="1.0.0",
)

# CORS — permitir requests del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir al dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTENTICACIÓN (JWT + bcrypt)
# ============================================================

JWT_SECRET = os.environ.get("JWT_SECRET", "cagemind_dev_secret_change_in_prod_2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


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
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
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


def create_token(username: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "role": role, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="No autenticado")
    return verify_token(credentials.credentials)


async def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    return user


# ============================================================
# CALIBRACIÓN DE PROBABILIDADES
# ============================================================
# El modelo raw produce probabilidades no calibradas (ej: 100%, 95%)
# que no reflejan la realidad del MMA donde cualquiera puede ganar.
# Se aplica: 1) compresión hacia 50% + 2) cap duro de 85%.

PROB_CAP = 0.85      # Probabilidad máxima permitida
COMPRESSION = 0.75   # Factor de compresión (1.0 = sin cambio, 0.5 = muy conservador)


def calibrate_proba(prob_a: float, prob_b: float) -> tuple[float, float]:
    """
    Calibra probabilidades binarias para hacerlas más realistas.
    1. Comprime hacia 50% usando el factor COMPRESSION.
    2. Aplica cap duro de PROB_CAP.
    3. Re-normaliza para que sumen 1.0.
    """
    # Paso 1: Comprimir hacia 0.5
    ca = 0.5 + (prob_a - 0.5) * COMPRESSION
    cb = 0.5 + (prob_b - 0.5) * COMPRESSION

    # Paso 2: Aplicar cap
    ca = min(ca, PROB_CAP)
    cb = min(cb, PROB_CAP)

    # Paso 3: Re-normalizar para que sumen 1.0
    total = ca + cb
    ca = ca / total
    cb = cb / total

    return round(ca, 4), round(cb, 4)


# ============================================================
# CARGA DE MODELOS Y DATOS (al iniciar)
# ============================================================

models_bundle = None
fighter_cache = None
fighter_stats_cache = None


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def load_models():
    global models_bundle
    if models_bundle is None:
        with open(MODELS_PATH, "rb") as f:
            models_bundle = pickle.load(f)
    return models_bundle


def load_fighter_cache():
    """Carga todos los peleadores en memoria para búsquedas rápidas."""
    global fighter_cache
    if fighter_cache is None:
        conn = get_db()
        rows = conn.execute("""
            SELECT name, height_inches, reach_inches, weight_lbs, stance,
                   wins, losses, draws, dob,
                   slpm, str_acc, sapm, str_def,
                   td_avg, td_acc, td_def, sub_avg
            FROM fighters
            ORDER BY name
        """).fetchall()
        conn.close()
        fighter_cache = {row["name"]: dict(row) for row in rows}
    return fighter_cache


def load_fighter_stats_cache():
    """Carga stats agregadas por peleador."""
    global fighter_stats_cache
    if fighter_stats_cache is None:
        conn = get_db()
        # Stats agregadas por peleador (todas sus peleas)
        stats = conn.execute("""
            SELECT
                fs.fighter_name,
                COUNT(DISTINCT fs.fight_id) as total_fights,
                SUM(fs.knockdowns) as total_kd,
                SUM(fs.sig_strikes_landed) as total_sig_landed,
                SUM(fs.sig_strikes_attempted) as total_sig_attempted,
                SUM(fs.takedowns_landed) as total_td_landed,
                SUM(fs.takedowns_attempted) as total_td_attempted,
                SUM(fs.submission_attempts) as total_sub_att,
                SUM(fs.control_time_seconds) as total_ctrl,
                SUM(fs.head_landed) as total_head,
                SUM(fs.body_landed) as total_body,
                SUM(fs.leg_landed) as total_leg,
                SUM(fs.distance_landed) as total_distance,
                SUM(fs.clinch_landed) as total_clinch,
                SUM(fs.ground_landed) as total_ground,
                MAX(fs.round) as max_rounds
            FROM fight_stats fs
            GROUP BY fs.fighter_name
        """).fetchall()
        conn.close()
        fighter_stats_cache = {row["fighter_name"]: dict(row) for row in stats}
    return fighter_stats_cache


@app.on_event("startup")
async def startup():
    """Pre-carga modelos y datos al iniciar."""
    print("Inicializando tabla users...")
    init_users_table()
    print("Cargando modelos...")
    load_models()
    print("Cargando cache de peleadores...")
    load_fighter_cache()
    load_fighter_stats_cache()
    print("API lista!")


# ============================================================
# SCHEMAS (Pydantic)
# ============================================================

class PredictionRequest(BaseModel):
    fighter_a: str
    fighter_b: str


class FighterProfile(BaseModel):
    name: str
    height_inches: Optional[float] = None
    reach_inches: Optional[float] = None
    weight_lbs: Optional[int] = None
    stance: Optional[str] = None
    wins: int = 0
    losses: int = 0
    draws: int = 0
    dob: Optional[str] = None
    slpm: Optional[float] = None
    str_acc: Optional[float] = None
    sapm: Optional[float] = None
    str_def: Optional[float] = None
    td_avg: Optional[float] = None
    td_acc: Optional[float] = None
    td_def: Optional[float] = None
    sub_avg: Optional[float] = None


class PredictionResponse(BaseModel):
    fighter_a: str
    fighter_b: str
    winner: str
    winner_probability: float
    loser_probability: float
    method_prediction: dict
    goes_to_decision: dict
    round_prediction: dict
    fighter_a_profile: dict
    fighter_b_profile: dict


# ============================================================
# FEATURE COMPUTATION (para predicciones en vivo)
# ============================================================

def compute_live_features(name_a: str, name_b: str) -> np.ndarray:
    """
    Calcula las features para una predicción en vivo.
    Usa los datos más recientes disponibles de ambos peleadores.
    """
    bundle = load_models()
    feature_names = bundle["feature_names"]
    fighters = load_fighter_cache()
    stats = load_fighter_stats_cache()

    # Obtener info de ambos peleadores
    info_a = fighters.get(name_a)
    info_b = fighters.get(name_b)

    if not info_a:
        raise HTTPException(status_code=404, detail="Peleador no encontrado: " + name_a)
    if not info_b:
        raise HTTPException(status_code=404, detail="Peleador no encontrado: " + name_b)

    stats_a = stats.get(name_a, {})
    stats_b = stats.get(name_b, {})

    # Obtener historial de peleas para cada peleador
    conn = get_db()

    hist_a = get_fight_history(conn, name_a)
    hist_b = get_fight_history(conn, name_b)

    conn.close()

    # Calcular features para cada peleador
    feats_a = compute_features_for_fighter(info_a, stats_a, hist_a)
    feats_b = compute_features_for_fighter(info_b, stats_b, hist_b)

    # Agregar features de Sherdog (pre-UFC)
    try:
        conn2 = get_db()
        sherdog_a = conn2.execute(
            "SELECT * FROM sherdog_features WHERE name = ?", (name_a,)
        ).fetchone()
        sherdog_b = conn2.execute(
            "SELECT * FROM sherdog_features WHERE name = ?", (name_b,)
        ).fetchone()
        conn2.close()

        sherdog_keys = [
            "pre_ufc_fights", "pre_ufc_wr", "pre_ufc_ko_rate", "pre_ufc_sub_rate",
            "pre_ufc_dec_rate", "pre_ufc_finish_rate", "pre_ufc_ko_loss_rate",
            "pre_ufc_sub_loss_rate", "pre_ufc_streak", "total_pro_fights", "org_level",
        ]
        if sherdog_a:
            sa = dict(sherdog_a)
            for k in sherdog_keys:
                feats_a[k] = sa.get(k, 0) or 0
        if sherdog_b:
            sb = dict(sherdog_b)
            for k in sherdog_keys:
                feats_b[k] = sb.get(k, 0) or 0
    except Exception:
        pass  # Si no existe la tabla, seguir sin Sherdog

    # Construir vector de features en el orden correcto
    feature_vector = []
    for fname in feature_names:
        if fname.startswith("a_"):
            key = fname[2:]
            feature_vector.append(feats_a.get(key, 0) or 0)
        elif fname.startswith("b_"):
            key = fname[2:]
            feature_vector.append(feats_b.get(key, 0) or 0)
        elif fname.startswith("diff_"):
            key = fname[5:]
            va = feats_a.get(key, 0) or 0
            vb = feats_b.get(key, 0) or 0
            feature_vector.append(va - vb)
        elif fname == "style_matchup":
            sa = feats_a.get("striking_score", 0) or 0
            ga = feats_a.get("grappling_score", 0) or 0
            sb = feats_b.get("striking_score", 0) or 0
            gb = feats_b.get("grappling_score", 0) or 0
            feature_vector.append((ga - sa) - (gb - sb))
        else:
            feature_vector.append(0)

    return np.array(feature_vector).reshape(1, -1)


def get_fight_history(conn, fighter_name):
    """Obtiene el historial de peleas de un peleador."""
    rows = conn.execute("""
        SELECT f.fight_id, f.winner_name, f.method, f.round,
               f.fighter_a_name, f.fighter_b_name,
               e.date_parsed
        FROM fights f
        JOIN events e ON f.event_id = e.event_id
        WHERE f.fighter_a_name = ? OR f.fighter_b_name = ?
        ORDER BY e.date_parsed
    """, (fighter_name, fighter_name)).fetchall()
    return [dict(r) for r in rows]


def safe_div(a, b, default=0):
    if b is None or b == 0 or a is None:
        return default
    return a / b


def compute_features_for_fighter(info, stats, history):
    """Calcula todas las features de un peleador."""
    feat = {}
    n = len(history)
    feat["experience"] = n

    # Físicas
    feat["height"] = info.get("height_inches")
    feat["reach"] = info.get("reach_inches")
    feat["weight"] = info.get("weight_lbs")

    # Edad
    dob = info.get("dob")
    if dob:
        for fmt in ["%b %d, %Y", "%B %d, %Y"]:
            try:
                dob_dt = datetime.strptime(str(dob).strip(), fmt)
                feat["age"] = (datetime.now() - dob_dt).days / 365.25
                break
            except ValueError:
                continue
    if "age" not in feat:
        feat["age"] = None

    # Stance
    stance = info.get("stance")
    feat["is_orthodox"] = 1 if stance == "Orthodox" else 0
    feat["is_southpaw"] = 1 if stance == "Southpaw" else 0
    feat["is_switch"] = 1 if stance == "Switch" else 0

    # Win rate
    wins = info.get("wins", 0) or 0
    losses = info.get("losses", 0) or 0
    feat["wins"] = wins
    feat["losses"] = losses
    feat["win_rate"] = safe_div(wins, wins + losses, 0.5)

    # Racha
    streak = 0
    streak_type = None
    for h in reversed(history):
        won = (h.get("winner_name") == info.get("name"))
        if streak == 0:
            streak_type = "W" if won else "L"
            streak = 1
        elif (won and streak_type == "W") or (not won and streak_type == "L"):
            streak += 1
        else:
            break
    feat["streak"] = streak if streak_type == "W" else -streak
    feat["abs_streak"] = streak

    # Estabilidad
    results = []
    for h in history:
        winner = h.get("winner_name")
        if winner:
            results.append(1 if winner == info.get("name") else 0)
    if len(results) >= 4:
        changes = sum(1 for i in range(1, len(results)) if results[i] != results[i-1])
        feat["stability"] = 1 - (changes / (len(results) - 1))
    else:
        feat["stability"] = None

    # Career stats from fighter table
    feat["career_sig_landed_pm"] = info.get("slpm", 0) or 0
    feat["career_sig_acc"] = info.get("str_acc", 0) or 0
    feat["career_sig_absorbed_pm"] = info.get("sapm", 0) or 0
    feat["career_sig_def"] = info.get("str_def", 0) or 0
    feat["career_td_landed_pm"] = info.get("td_avg", 0) or 0
    feat["career_td_acc"] = info.get("td_acc", 0) or 0
    feat["career_td_def"] = info.get("td_def", 0) or 0
    feat["career_sub_avg"] = info.get("sub_avg", 0) or 0

    # Stats from aggregated fight_stats
    total_fights = stats.get("total_fights", 1) or 1
    total_time = total_fights * 15  # Aproximación: 3 rounds x 5 min

    feat["career_kd_pm"] = safe_div(stats.get("total_kd", 0), total_time)
    feat["career_ctrl_pm"] = safe_div(stats.get("total_ctrl", 0), total_time)
    feat["career_sig_attempted_pm"] = safe_div(stats.get("total_sig_attempted", 0), total_time)
    feat["career_td_attempted_pm"] = safe_div(stats.get("total_td_attempted", 0), total_time)

    # Strike distribution
    total_sig = stats.get("total_sig_landed", 0) or 1
    feat["pct_head"] = safe_div(stats.get("total_head", 0), total_sig)
    feat["pct_body"] = safe_div(stats.get("total_body", 0), total_sig)
    feat["pct_leg"] = safe_div(stats.get("total_leg", 0), total_sig)
    feat["pct_distance"] = safe_div(stats.get("total_distance", 0), total_sig)
    feat["pct_clinch"] = safe_div(stats.get("total_clinch", 0), total_sig)
    feat["pct_ground"] = safe_div(stats.get("total_ground", 0), total_sig)

    # Eficiencia
    feat["strike_efficiency"] = feat["career_sig_acc"]
    feat["td_efficiency"] = feat["career_td_acc"]

    # Recent stats (últimas 5 peleas) — aproximación con career stats
    feat["recent_sig_landed_pm"] = feat["career_sig_landed_pm"]
    feat["recent_sig_acc"] = feat["career_sig_acc"]
    feat["recent_td_landed_pm"] = feat["career_td_landed_pm"]
    feat["recent_kd_pm"] = feat["career_kd_pm"]

    # Recent win rate (últimas 5)
    recent_results = results[-5:] if len(results) >= 5 else results
    feat["recent_win_rate"] = np.mean(recent_results) if len(recent_results) > 0 else 0.5

    # Método de victoria/derrota
    win_methods = []
    loss_methods = []
    for h in history:
        method = (h.get("method") or "").upper()
        won = h.get("winner_name") == info.get("name")
        m_type = "dec"
        if "KO" in method or "TKO" in method:
            m_type = "ko"
        elif "SUB" in method:
            m_type = "sub"

        if won:
            win_methods.append(m_type)
        elif h.get("winner_name"):
            loss_methods.append(m_type)

    n_wins = len(win_methods)
    n_losses = len(loss_methods)

    feat["finish_rate"] = safe_div(sum(1 for m in win_methods if m in ["ko", "sub"]), n_wins)
    feat["ko_rate"] = safe_div(sum(1 for m in win_methods if m == "ko"), n_wins)
    feat["sub_rate"] = safe_div(sum(1 for m in win_methods if m == "sub"), n_wins)
    feat["dec_rate"] = safe_div(sum(1 for m in win_methods if m == "dec"), n_wins)
    feat["ko_loss_rate"] = safe_div(sum(1 for m in loss_methods if m == "ko"), n_losses)
    feat["sub_loss_rate"] = safe_div(sum(1 for m in loss_methods if m == "sub"), n_losses)
    feat["dec_loss_rate"] = safe_div(sum(1 for m in loss_methods if m == "dec"), n_losses)

    # Round promedio de finalización
    finish_rounds = [h["round"] for h in history
                     if h.get("winner_name") == info.get("name")
                     and ("KO" in (h.get("method") or "").upper() or "SUB" in (h.get("method") or "").upper())
                     and h.get("round") is not None]
    feat["avg_finish_round"] = np.mean(finish_rounds) if finish_rounds else None

    # Inactividad
    if history:
        last_date = history[-1].get("date_parsed")
        if last_date:
            try:
                last_dt = pd.to_datetime(last_date)
                feat["days_inactive"] = (pd.Timestamp.now() - last_dt).days
            except Exception:
                feat["days_inactive"] = None
        else:
            feat["days_inactive"] = None
    else:
        feat["days_inactive"] = None

    # Estilo scores
    feat["striking_score"] = feat["career_sig_landed_pm"] + feat.get("pct_distance", 0) * 2
    feat["grappling_score"] = (feat["career_td_landed_pm"] * 10 +
                                feat["career_sub_avg"] * 15 +
                                feat["career_ctrl_pm"] +
                                feat.get("pct_ground", 0) * 3)

    # Calidad de oponentes (aproximación con career WR)
    feat["avg_opp_wr"] = 0.5  # Default — se calcularía mejor con historial completo

    # Cardio ratio
    feat["cardio_ratio"] = None

    return feat


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "UFC Fight Predictor API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": ["/fighters", "/fighters/{name}", "/predict", "/upcoming", "/stats"],
        "docs": "/docs"
    }


@app.get("/fighters")
async def list_fighters(
    search: str = Query(default="", description="Buscar por nombre"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    min_fights: int = Query(default=0, ge=0, description="Minimo de peleas"),
):
    """Lista peleadores con búsqueda opcional."""
    conn = get_db()

    query = "SELECT name, wins, losses, draws, weight_lbs, stance, height_inches, reach_inches FROM fighters"
    params = []
    conditions = []

    if search:
        conditions.append("LOWER(name) LIKE ?")
        params.append("%" + search.lower() + "%")

    if min_fights > 0:
        conditions.append("(wins + losses + draws) >= ?")
        params.append(min_fights)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY (wins + losses + draws) DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "count": len(rows),
        "fighters": [dict(r) for r in rows]
    }


@app.get("/fighters/{name}")
async def get_fighter(name: str):
    """Perfil detallado de un peleador."""
    fighters = load_fighter_cache()
    stats = load_fighter_stats_cache()

    # Buscar por nombre exacto o parcial
    info = fighters.get(name)
    if not info:
        # Buscar parcial
        matches = [n for n in fighters if name.lower() in n.lower()]
        if len(matches) == 1:
            info = fighters[matches[0]]
            name = matches[0]
        elif len(matches) > 1:
            return {"error": "Múltiples coincidencias", "matches": matches[:10]}
        else:
            raise HTTPException(status_code=404, detail="Peleador no encontrado")

    fighter_stats = stats.get(name, {})

    conn = get_db()
    # Últimas 5 peleas
    recent_fights = conn.execute("""
        SELECT f.fighter_a_name, f.fighter_b_name, f.winner_name,
               f.method, f.round, f.weight_class, e.date_parsed
        FROM fights f
        JOIN events e ON f.event_id = e.event_id
        WHERE f.fighter_a_name = ? OR f.fighter_b_name = ?
        ORDER BY e.date_parsed DESC
        LIMIT 5
    """, (name, name)).fetchall()
    conn.close()

    recent = []
    for r in recent_fights:
        opponent = r["fighter_b_name"] if r["fighter_a_name"] == name else r["fighter_a_name"]
        won = r["winner_name"] == name
        recent.append({
            "opponent": opponent,
            "result": "W" if won else ("L" if r["winner_name"] else "NC/Draw"),
            "method": r["method"],
            "round": r["round"],
            "date": r["date_parsed"],
        })

    return {
        "profile": info,
        "career_stats": fighter_stats,
        "recent_fights": recent,
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict_fight(request: PredictionRequest):
    """
    Predice el resultado de una pelea entre dos peleadores.
    Retorna: ganador, probabilidad, método probable, round probable.
    """
    bundle = load_models()
    name_a = request.fighter_a
    name_b = request.fighter_b

    fighters = load_fighter_cache()

    # Validar que existan
    if name_a not in fighters:
        matches = [n for n in fighters if name_a.lower() in n.lower()]
        if len(matches) == 1:
            name_a = matches[0]
        else:
            raise HTTPException(status_code=404,
                                detail="Peleador A no encontrado: " + request.fighter_a +
                                       (". Coincidencias: " + str(matches[:5]) if matches else ""))

    if name_b not in fighters:
        matches = [n for n in fighters if name_b.lower() in n.lower()]
        if len(matches) == 1:
            name_b = matches[0]
        else:
            raise HTTPException(status_code=404,
                                detail="Peleador B no encontrado: " + request.fighter_b +
                                       (". Coincidencias: " + str(matches[:5]) if matches else ""))

    # Calcular features
    X = compute_live_features(name_a, name_b)

    # === Modelo 1: Quién gana ===
    winner_model = bundle["winner_model"]
    winner_proba = winner_model.predict_proba(X)[0]
    raw_a = float(winner_proba[1])  # P(A gana) raw
    raw_b = float(winner_proba[0])  # P(B gana) raw
    prob_a, prob_b = calibrate_proba(raw_a, raw_b)
    winner = name_a if prob_a > prob_b else name_b
    winner_prob = max(prob_a, prob_b)
    loser_prob = min(prob_a, prob_b)

    # === Modelo 2: Cómo gana ===
    method_model = bundle["method_model"]
    method_encoder = bundle["method_encoder"]
    method_proba = method_model.predict_proba(X)[0]
    method_classes = list(method_encoder.classes_)
    method_dict = {}
    for cls, prob in zip(method_classes, method_proba):
        label = {"ko": "KO/TKO", "sub": "Submission", "dec": "Decision"}.get(cls, cls)
        method_dict[label] = round(float(prob), 4)

    # === Modelo 3: Llega a decisión ===
    distance_model = bundle["distance_model"]
    dist_proba = distance_model.predict_proba(X)[0]
    distance_dict = {
        "finish": round(float(dist_proba[0]), 4),
        "decision": round(float(dist_proba[1]), 4),
    }

    # === Modelo 4: En qué round ===
    round_model = bundle["round_model"]
    round_proba = round_model.predict_proba(X)[0]
    round_labels = ["Round 1", "Round 2", "Round 3", "Round 4+"]
    round_dict = {}
    for lbl, prob in zip(round_labels, round_proba):
        round_dict[lbl] = round(float(prob), 4)

    # Perfiles resumidos
    info_a = fighters[name_a]
    info_b = fighters[name_b]

    return PredictionResponse(
        fighter_a=name_a,
        fighter_b=name_b,
        winner=winner,
        winner_probability=winner_prob,
        loser_probability=loser_prob,
        method_prediction=method_dict,
        goes_to_decision=distance_dict,
        round_prediction=round_dict,
        fighter_a_profile={
            "name": name_a,
            "record": str(info_a.get("wins", 0)) + "-" + str(info_a.get("losses", 0)) + "-" + str(info_a.get("draws", 0)),
            "height": info_a.get("height_inches"),
            "reach": info_a.get("reach_inches"),
            "weight": info_a.get("weight_lbs"),
            "stance": info_a.get("stance"),
            "win_probability": prob_a,
        },
        fighter_b_profile={
            "name": name_b,
            "record": str(info_b.get("wins", 0)) + "-" + str(info_b.get("losses", 0)) + "-" + str(info_b.get("draws", 0)),
            "height": info_b.get("height_inches"),
            "reach": info_b.get("reach_inches"),
            "weight": info_b.get("weight_lbs"),
            "stance": info_b.get("stance"),
            "win_probability": prob_b,
        },
    )


@app.get("/events")
async def get_events(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=1, ge=1, le=1),
):
    """
    Retorna eventos paginados (1 por página para navegación tipo libro).
    Incluye todas las peleas con predicciones retroactivas y resultados reales.
    """
    conn = get_db()

    # Total de eventos
    total = conn.execute("""
        SELECT COUNT(*) FROM events e
        WHERE e.date_parsed IS NOT NULL
        AND EXISTS (SELECT 1 FROM fights f WHERE f.event_id = e.event_id)
    """).fetchone()[0]

    # Obtener el evento de esta página (ordenado por fecha desc)
    offset = (page - 1)
    event_row = conn.execute("""
        SELECT e.event_id, e.name, e.date_parsed, e.location
        FROM events e
        WHERE e.date_parsed IS NOT NULL
        AND EXISTS (SELECT 1 FROM fights f WHERE f.event_id = e.event_id)
        ORDER BY e.date_parsed DESC
        LIMIT 1 OFFSET ?
    """, (offset,)).fetchone()

    if not event_row:
        conn.close()
        return {"total_events": total, "page": page, "event": None, "fights": []}

    event = dict(event_row)

    # Obtener peleas de este evento
    fight_rows = conn.execute("""
        SELECT f.fight_id, f.fighter_a_name, f.fighter_b_name,
               f.winner_name, f.method, f.round, f.time,
               f.weight_class, f.is_draw, f.is_no_contest
        FROM fights f
        WHERE f.event_id = ?
    """, (event["event_id"],)).fetchall()

    conn.close()

    # Generar predicciones retroactivas para cada pelea
    fighters = load_fighter_cache()
    fights_with_predictions = []

    for fight_row in fight_rows:
        fight = dict(fight_row)
        fa = fight["fighter_a_name"]
        fb = fight["fighter_b_name"]

        # Intentar predecir
        pred = None
        try:
            if fa in fighters and fb in fighters:
                X = compute_live_features(fa, fb)
                bundle = load_models()

                winner_proba = bundle["winner_model"].predict_proba(X)[0]
                raw_a = float(winner_proba[1])
                raw_b = float(winner_proba[0])
                prob_a, prob_b = calibrate_proba(raw_a, raw_b)
                predicted_winner = fa if prob_a > prob_b else fb

                method_proba = bundle["method_model"].predict_proba(X)[0]
                method_classes = list(bundle["method_encoder"].classes_)
                method_dict = {}
                for cls, prob in zip(method_classes, method_proba):
                    label = {"ko": "KO/TKO", "sub": "Submission", "dec": "Decision"}.get(cls, cls)
                    method_dict[label] = round(float(prob), 4)

                pred = {
                    "predicted_winner": predicted_winner,
                    "prob_a": prob_a,
                    "prob_b": prob_b,
                    "confidence": round(max(prob_a, prob_b), 4),
                    "method_prediction": method_dict,
                    "correct": predicted_winner == fight["winner_name"] if fight["winner_name"] else None,
                }
        except Exception:
            pass

        fights_with_predictions.append({
            "fighter_a": fa,
            "fighter_b": fb,
            "winner": fight["winner_name"],
            "method": fight["method"],
            "round": fight["round"],
            "time": fight["time"],
            "weight_class": fight["weight_class"],
            "is_draw": fight["is_draw"],
            "is_no_contest": fight["is_no_contest"],
            "prediction": pred,
        })

    # Calcular accuracy del modelo para este evento
    predictions_made = [f for f in fights_with_predictions if f["prediction"] and f["prediction"]["correct"] is not None]
    correct = sum(1 for f in predictions_made if f["prediction"]["correct"])
    total_predicted = len(predictions_made)

    return {
        "total_events": total,
        "page": page,
        "total_pages": total,
        "event": event,
        "fights": fights_with_predictions,
        "model_accuracy": {
            "correct": correct,
            "total": total_predicted,
            "percentage": round(correct / total_predicted * 100, 1) if total_predicted > 0 else 0,
        },
    }


@app.get("/upcoming")
async def get_upcoming():
    """
    Retorna eventos próximos (futuros) con predicciones pre-calculadas.
    Filtra automáticamente: solo eventos cuya fecha >= hoy.
    Los eventos pasados se quedan en /events (histórico).
    """
    upcoming_file = Path("data/raw/ufcstats/upcoming_events.json")

    if not upcoming_file.exists():
        return {"events": [], "message": "No hay datos de upcoming. Ejecuta: python scrape_upcoming.py"}

    import json as _json
    from datetime import datetime, date

    with open(upcoming_file, "r", encoding="utf-8") as f:
        all_events = _json.load(f)

    # Filtrar solo eventos futuros (fecha >= hoy)
    today = date.today()
    events = []
    for ev in all_events:
        try:
            ev_date = datetime.strptime(ev["date"], "%B %d, %Y").date()
            if ev_date >= today:
                events.append(ev)
        except (ValueError, KeyError, TypeError):
            events.append(ev)  # Si no se puede parsear la fecha, incluirlo

    fighters = load_fighter_cache()
    bundle = load_models()

    result_events = []
    for event in events:
        fights_with_pred = []
        for fight in event.get("fights", []):
            fa = fight["fighter_a"]
            fb = fight["fighter_b"]

            pred = None
            try:
                if fa in fighters and fb in fighters:
                    X = compute_live_features(fa, fb)

                    winner_proba = bundle["winner_model"].predict_proba(X)[0]
                    raw_a = float(winner_proba[1])
                    raw_b = float(winner_proba[0])
                    prob_a, prob_b = calibrate_proba(raw_a, raw_b)
                    predicted_winner = fa if prob_a > prob_b else fb

                    method_proba = bundle["method_model"].predict_proba(X)[0]
                    method_classes = list(bundle["method_encoder"].classes_)
                    method_dict = {}
                    for cls, prob in zip(method_classes, method_proba):
                        label = {"ko": "KO/TKO", "sub": "Submission", "dec": "Decision"}.get(cls, cls)
                        method_dict[label] = round(float(prob), 4)

                    dist_proba = bundle["distance_model"].predict_proba(X)[0]

                    round_proba = bundle["round_model"].predict_proba(X)[0]
                    round_labels = ["Round 1", "Round 2", "Round 3", "Round 4+"]
                    round_dict = {lbl: round(float(p), 4) for lbl, p in zip(round_labels, round_proba)}

                    info_a = fighters[fa]
                    info_b = fighters[fb]

                    pred = {
                        "predicted_winner": predicted_winner,
                        "prob_a": prob_a,
                        "prob_b": prob_b,
                        "confidence": round(max(prob_a, prob_b), 4),
                        "method_prediction": method_dict,
                        "goes_to_decision": {
                            "finish": round(float(dist_proba[0]), 4),
                            "decision": round(float(dist_proba[1]), 4),
                        },
                        "round_prediction": round_dict,
                        "fighter_a_profile": {
                            "record": str(info_a.get("wins", 0)) + "-" + str(info_a.get("losses", 0)) + "-" + str(info_a.get("draws", 0)),
                            "weight": info_a.get("weight_lbs"),
                            "stance": info_a.get("stance"),
                        },
                        "fighter_b_profile": {
                            "record": str(info_b.get("wins", 0)) + "-" + str(info_b.get("losses", 0)) + "-" + str(info_b.get("draws", 0)),
                            "weight": info_b.get("weight_lbs"),
                            "stance": info_b.get("stance"),
                        },
                    }
            except Exception:
                pass

            fights_with_pred.append({
                "fighter_a": fa,
                "fighter_b": fb,
                "weight_class": fight.get("weight_class"),
                "prediction": pred,
            })

        result_events.append({
            "name": event["name"],
            "date": event["date"],
            "location": event.get("location"),
            "fights": fights_with_pred,
            "total_fights": len(fights_with_pred),
            "predicted_fights": sum(1 for f in fights_with_pred if f["prediction"]),
        })

    return {"events": result_events, "total_events": len(result_events)}


@app.get("/stats")
async def get_stats():
    """Estadísticas generales de la base de datos."""
    conn = get_db()

    stats = {}
    for table in ["fighters", "events", "fights", "fight_stats"]:
        count = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        stats[table] = count

    # Último evento
    last_event = conn.execute("""
        SELECT name, date_parsed FROM events
        WHERE date_parsed IS NOT NULL
        ORDER BY date_parsed DESC LIMIT 1
    """).fetchone()

    # Top peleadores por victorias
    top_fighters = conn.execute("""
        SELECT name, wins, losses, draws FROM fighters
        ORDER BY wins DESC LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "database": stats,
        "last_event": dict(last_event) if last_event else None,
        "top_fighters_by_wins": [dict(f) for f in top_fighters],
        "model_info": {
            "features": len(load_models()["feature_names"]),
            "models": ["winner", "method", "distance", "round"],
        }
    }


# ============================================================
# AUTH ENDPOINTS
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
async def login(req: LoginRequest):
    """Autenticación con username y password. Devuelve JWT."""
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, password, role FROM users WHERE username = ?",
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


@app.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """Devuelve info del usuario autenticado."""
    return {"username": user["sub"], "role": user["role"]}


# ============================================================
# ADMIN ENDPOINTS (requieren rol admin)
# ============================================================

@app.get("/admin/dashboard")
async def admin_dashboard(user: dict = Depends(require_admin)):
    """Dashboard del panel admin con stats completas."""
    conn = get_db()

    # Conteos de BD
    db_stats = {}
    for table in ["fighters", "events", "fights", "fight_stats"]:
        db_stats[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    # Último evento
    last_event = conn.execute("""
        SELECT name, date_parsed, location FROM events
        WHERE date_parsed IS NOT NULL
        ORDER BY date_parsed DESC LIMIT 1
    """).fetchone()

    # Accuracy del modelo (desde eventos históricos con resultados)
    total_fights_w_winner = conn.execute("""
        SELECT COUNT(*) FROM fights WHERE winner_name IS NOT NULL AND winner_name != ''
    """).fetchone()[0]

    # Eventos recientes (últimos 5)
    recent_events = conn.execute("""
        SELECT e.name, e.date_parsed, e.location,
               COUNT(f.fight_id) as total_fights
        FROM events e
        LEFT JOIN fights f ON e.event_id = f.event_id
        WHERE e.date_parsed IS NOT NULL
        GROUP BY e.event_id
        ORDER BY e.date_parsed DESC
        LIMIT 5
    """).fetchall()

    # Top 10 peleadores activos (más peleas recientes)
    top_active = conn.execute("""
        SELECT f.name, f.wins, f.losses, f.draws,
               f.weight_lbs, f.stance
        FROM fighters f
        WHERE f.wins + f.losses >= 5
        ORDER BY f.wins DESC
        LIMIT 10
    """).fetchall()

    # Distribución de métodos de victoria
    methods = conn.execute("""
        SELECT
            CASE
                WHEN UPPER(method) LIKE '%KO%' OR UPPER(method) LIKE '%TKO%' THEN 'KO/TKO'
                WHEN UPPER(method) LIKE '%SUB%' THEN 'Submission'
                WHEN UPPER(method) LIKE '%DEC%' THEN 'Decision'
                ELSE 'Otro'
            END as method_group,
            COUNT(*) as count
        FROM fights
        WHERE winner_name IS NOT NULL AND winner_name != ''
        GROUP BY method_group
        ORDER BY count DESC
    """).fetchall()

    # Info del modelo
    bundle = load_models()
    model_info = {
        "features": len(bundle.get("feature_names", [])),
        "models": list(bundle.get("models", {}).keys()) if isinstance(bundle.get("models"), dict) else ["winner", "method", "distance", "round"],
    }

    # Peleas por año (últimos 10 años)
    fights_by_year = conn.execute("""
        SELECT SUBSTR(e.date_parsed, 1, 4) as year, COUNT(f.fight_id) as count
        FROM fights f
        JOIN events e ON f.event_id = e.event_id
        WHERE e.date_parsed IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "database": db_stats,
        "last_event": dict(last_event) if last_event else None,
        "recent_events": [dict(e) for e in recent_events],
        "top_active_fighters": [dict(f) for f in top_active],
        "method_distribution": [dict(m) for m in methods],
        "model_info": model_info,
        "fights_by_year": [dict(f) for f in fights_by_year],
        "total_fights_with_result": total_fights_w_winner,
    }


# ============================================================
# ANALYTICS ENDPOINTS
# ============================================================

class TrackEvent(BaseModel):
    event_type: str       # page_view, prediction, search
    page: Optional[str] = None
    detail: Optional[str] = None


@app.post("/analytics/track")
async def track_event(event: TrackEvent):
    """Registra un evento de analytics (público, no requiere auth)."""
    conn = get_db()
    conn.execute(
        "INSERT INTO analytics_events (event_type, page, detail) VALUES (?, ?, ?)",
        (event.event_type, event.page, event.detail),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/admin/analytics")
async def get_analytics(user: dict = Depends(require_admin)):
    """Estadísticas de uso del sistema."""
    conn = get_db()

    # Total de eventos
    total_events = conn.execute("SELECT COUNT(*) FROM analytics_events").fetchone()[0]

    # Eventos por tipo
    by_type = conn.execute("""
        SELECT event_type, COUNT(*) as count
        FROM analytics_events
        GROUP BY event_type
        ORDER BY count DESC
    """).fetchall()

    # Page views por sección
    by_page = conn.execute("""
        SELECT page, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'page_view' AND page IS NOT NULL
        GROUP BY page
        ORDER BY count DESC
    """).fetchall()

    # Predicciones por día (últimos 14 días)
    predictions_daily = conn.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'prediction'
        GROUP BY day
        ORDER BY day DESC
        LIMIT 14
    """).fetchall()

    # Peleadores más buscados
    top_searched = conn.execute("""
        SELECT detail, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'search' AND detail IS NOT NULL AND detail != ''
        GROUP BY detail
        ORDER BY count DESC
        LIMIT 15
    """).fetchall()

    # Predicciones más populares (pares de peleadores)
    top_predictions = conn.execute("""
        SELECT detail, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'prediction' AND detail IS NOT NULL
        GROUP BY detail
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    # Actividad por hora (distribución)
    by_hour = conn.execute("""
        SELECT CAST(STRFTIME('%H', created_at) AS INTEGER) as hour, COUNT(*) as count
        FROM analytics_events
        GROUP BY hour
        ORDER BY hour
    """).fetchall()

    conn.close()

    return {
        "total_events": total_events,
        "by_type": [dict(r) for r in by_type],
        "by_page": [dict(r) for r in by_page],
        "predictions_daily": [dict(r) for r in predictions_daily],
        "top_searched": [dict(r) for r in top_searched],
        "top_predictions": [dict(r) for r in top_predictions],
        "by_hour": [dict(r) for r in by_hour],
    }


# ============================================================
# UPDATE / SCRAPER ENDPOINTS (admin)
# ============================================================

@app.post("/admin/update")
async def trigger_update(user: dict = Depends(require_admin)):
    """
    Ejecuta el scraper de upcoming events.
    Corre scrape_upcoming.py y registra el resultado.
    """
    import subprocess as sp

    conn = get_db()
    conn.execute(
        "INSERT INTO update_logs (action, status) VALUES (?, ?)",
        ("upcoming", "running"),
    )
    conn.commit()
    log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    try:
        result = sp.run(
            [sys.executable, "scrape_upcoming.py"],
            capture_output=True, text=True, timeout=120,
            cwd=str(Path(__file__).parent.parent),
        )
        status = "success" if result.returncode == 0 else "error"
        output = (result.stdout or "") + (result.stderr or "")
        # Truncar output si es muy largo
        if len(output) > 2000:
            output = output[:2000] + "... (truncated)"
    except sp.TimeoutExpired:
        status = "error"
        output = "Timeout: el scraper tardó más de 2 minutos"
    except Exception as e:
        status = "error"
        output = str(e)

    conn = get_db()
    conn.execute(
        "UPDATE update_logs SET status = ?, result = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, output, log_id),
    )
    conn.commit()
    conn.close()

    return {"status": status, "log_id": log_id, "output": output[:500]}


@app.get("/admin/update-logs")
async def get_update_logs(user: dict = Depends(require_admin)):
    """Historial de actualizaciones."""
    conn = get_db()
    logs = conn.execute("""
        SELECT id, action, status, result, started_at, finished_at
        FROM update_logs
        ORDER BY started_at DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    return {"logs": [dict(l) for l in logs]}


# ============================================================
# REGISTRO PÚBLICO
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


@app.post("/auth/register")
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
    if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Ese usuario ya existe")
    if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Ese email ya está registrado")

    hashed = pwd_context.hash(req.password)
    conn.execute(
        "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
        (username, email, hashed, "user"),
    )
    conn.commit()
    conn.close()

    token = create_token(username, "user")
    return {"token": token, "username": username, "role": "user"}


# ============================================================
# PICKS (Votación)
# ============================================================

class PickRequest(BaseModel):
    event_name: str
    fighter_a: str
    fighter_b: str
    picked_winner: str


@app.post("/picks")
async def submit_pick(pick: PickRequest, user: dict = Depends(get_current_user)):
    """Enviar o actualizar un pick para una pelea."""
    if pick.picked_winner not in [pick.fighter_a, pick.fighter_b]:
        raise HTTPException(status_code=400, detail="El pick debe ser uno de los dos peleadores")

    conn = get_db()
    db_user = conn.execute("SELECT id FROM users WHERE username = ?", (user["sub"],)).fetchone()
    if not db_user:
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_id = db_user["id"]

    # Upsert: si ya existe el pick para esta pelea, actualizarlo
    existing = conn.execute(
        "SELECT id FROM picks WHERE user_id = ? AND event_name = ? AND fighter_a = ? AND fighter_b = ?",
        (user_id, pick.event_name, pick.fighter_a, pick.fighter_b),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE picks SET picked_winner = ?, created_at = CURRENT_TIMESTAMP WHERE id = ?",
            (pick.picked_winner, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO picks (user_id, event_name, fighter_a, fighter_b, picked_winner) VALUES (?, ?, ?, ?, ?)",
            (user_id, pick.event_name, pick.fighter_a, pick.fighter_b, pick.picked_winner),
        )

    conn.commit()
    conn.close()
    return {"ok": True, "picked_winner": pick.picked_winner}


@app.get("/picks/{event_name}")
async def get_picks(event_name: str, user: dict = Depends(get_current_user)):
    """Obtener los picks del usuario para un evento."""
    conn = get_db()
    db_user = conn.execute("SELECT id FROM users WHERE username = ?", (user["sub"],)).fetchone()
    if not db_user:
        conn.close()
        return {"picks": []}

    picks = conn.execute(
        "SELECT fighter_a, fighter_b, picked_winner FROM picks WHERE user_id = ? AND event_name = ?",
        (db_user["id"], event_name),
    ).fetchall()
    conn.close()
    return {"picks": [dict(p) for p in picks]}


@app.get("/leaderboard")
async def get_leaderboard():
    """
    Leaderboard: compara accuracy de usuarios vs CageMind.
    Solo cuenta peleas que ya tienen resultado (winner_name en fights).
    """
    conn = get_db()

    # Obtener todos los picks con resultado real
    rows = conn.execute("""
        SELECT
            u.username,
            p.event_name,
            p.fighter_a,
            p.fighter_b,
            p.picked_winner,
            f.winner_name
        FROM picks p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN fights f ON (
            (f.fighter_a_name = p.fighter_a AND f.fighter_b_name = p.fighter_b)
            OR (f.fighter_a_name = p.fighter_b AND f.fighter_b_name = p.fighter_a)
        )
        WHERE f.winner_name IS NOT NULL AND f.winner_name != ''
    """).fetchall()

    # Calcular stats por usuario
    user_stats: dict = {}
    for row in rows:
        username = row["username"]
        if username not in user_stats:
            user_stats[username] = {"correct": 0, "total": 0}
        user_stats[username]["total"] += 1
        if row["picked_winner"] == row["winner_name"]:
            user_stats[username]["correct"] += 1

    # Calcular accuracy de CageMind (modelo) en las mismas peleas
    model_correct = 0
    model_total = 0
    fighters = load_fighter_cache()
    bundle = load_models()

    seen_fights: set = set()
    for row in rows:
        fight_key = f"{row['fighter_a']}|{row['fighter_b']}"
        if fight_key in seen_fights:
            continue
        seen_fights.add(fight_key)

        try:
            features = compute_live_features(row["fighter_a"], row["fighter_b"])
            winner_model = bundle["models"]["winner"]
            proba = winner_model.predict_proba(features)[0]
            predicted = row["fighter_a"] if proba[1] > 0.5 else row["fighter_b"]
            model_total += 1
            if predicted == row["winner_name"]:
                model_correct += 1
        except Exception:
            pass

    conn.close()

    # Build leaderboard
    leaderboard = []
    for username, stats in user_stats.items():
        pct = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
        leaderboard.append({
            "username": username,
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": pct,
        })

    leaderboard.sort(key=lambda x: (-x["accuracy"], -x["total"]))

    model_accuracy = round(model_correct / model_total * 100, 1) if model_total > 0 else 0

    return {
        "leaderboard": leaderboard,
        "cagemind": {
            "correct": model_correct,
            "total": model_total,
            "accuracy": model_accuracy,
        },
    }


# ============================================================
# ADMIN: Picks Stats
# ============================================================

@app.get("/admin/picks-stats")
async def admin_picks_stats(user: dict = Depends(require_admin)):
    """Estadísticas de votación para admin."""
    conn = get_db()

    total_picks = conn.execute("SELECT COUNT(*) FROM picks").fetchone()[0]
    total_voters = conn.execute("SELECT COUNT(DISTINCT user_id) FROM picks").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'user'").fetchone()[0]

    # Picks por evento
    by_event = conn.execute("""
        SELECT event_name, COUNT(*) as picks, COUNT(DISTINCT user_id) as voters
        FROM picks
        GROUP BY event_name
        ORDER BY event_name DESC
    """).fetchall()

    # Peleas más votadas
    top_fights = conn.execute("""
        SELECT event_name, fighter_a, fighter_b,
               COUNT(*) as total_picks,
               SUM(CASE WHEN picked_winner = fighter_a THEN 1 ELSE 0 END) as picks_a,
               SUM(CASE WHEN picked_winner = fighter_b THEN 1 ELSE 0 END) as picks_b
        FROM picks
        GROUP BY event_name, fighter_a, fighter_b
        ORDER BY total_picks DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "total_picks": total_picks,
        "total_voters": total_voters,
        "total_users": total_users,
        "by_event": [dict(r) for r in by_event],
        "top_fights": [dict(r) for r in top_fights],
    }