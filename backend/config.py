"""
Configuración del backend — rutas, constantes y parámetros.
"""
from __future__ import annotations

import os
from pathlib import Path

# ============================================================
# RUTAS
# ============================================================

DB_PATH = Path("db/ufc_predictor.db")
MODELS_PATH = Path("ml/models/ufc_predictor_models.pkl")
FEATURES_PATH = Path("ml/models/feature_names.json")

# ============================================================
# CALIBRACIÓN DE PROBABILIDADES
# ============================================================
# El modelo raw produce probabilidades no calibradas (ej: 100%, 95%)
# que no reflejan la realidad del MMA donde cualquiera puede ganar.
# Se aplica: 1) compresión hacia 50% + 2) cap duro de 85%.

PROB_CAP = 0.85      # Probabilidad máxima permitida
COMPRESSION = 0.75   # Factor de compresión (1.0 = sin cambio, 0.5 = muy conservador)

# ============================================================
# NEWCOMERS
# ============================================================

MIN_UFC_FIGHTS_FOR_RELIABLE = 3

# ============================================================
# AUTENTICACIÓN
# ============================================================

JWT_SECRET = os.environ.get("JWT_SECRET", "cagemind_dev_secret_change_in_prod_2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# ============================================================
# ODDS / VALUE BETS
# ============================================================

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"
VALUE_THRESHOLD = 0.10  # 10% edge mínimo para considerar value bet
