
from __future__ import annotations

import os
from pathlib import Path

# ============================================================
# RUTAS
# ============================================================

DB_PATH = Path("db/ufc_predictor.db")
SUPABASE_URL = os.environ.get("DATABASE_URL") 

if SUPABASE_URL:
    DATABASE_URL = SUPABASE_URL
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

MODELS_PATH = Path("ml/models/ufc_predictor_models.pkl")
FEATURES_PATH = Path("ml/models/feature_names.json")

# ============================================================
# CALIBRACIÓN DE PROBABILIDADES
# ============================================================


PROB_CAP = 0.85     
COMPRESSION = 0.75   

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
