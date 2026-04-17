from __future__ import annotations

import os
from pathlib import Path

DB_PATH = Path("db/ufc_predictor.db")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

MODELS_PATH = Path("ml/models/ufc_predictor_models.pkl")
FEATURES_PATH = Path("ml/models/feature_names.json")

PROB_CAP = 0.85
COMPRESSION = 0.75

MIN_UFC_FIGHTS_FOR_RELIABLE = 3

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET must be set in environment variables")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"
VALUE_THRESHOLD = 0.10
