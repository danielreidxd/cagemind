
from __future__ import annotations

import requests as http_requests

from backend.config import ODDS_API_KEY, ODDS_API_URL


def fetch_odds() -> list:
    """Obtiene odds actuales de The Odds API."""
    if not ODDS_API_KEY:
        return []
    try:
        resp = http_requests.get(ODDS_API_URL, params={
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def american_to_prob(odds: int) -> float:
    """Convierte odds americanas a probabilidad implícita."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def normalize_name(name: str) -> str:
    """Normaliza nombre para matching entre APIs."""
    return name.strip().lower().replace(".", "").replace("'", "")


def match_fighter_names(api_name: str, db_fighters: dict) -> str | None:
    """Intenta matchear un nombre de la API de odds con un nombre de la BD."""
    norm = normalize_name(api_name)
    for db_name in db_fighters:
        if normalize_name(db_name) == norm:
            return db_name
    # Partial match: apellido
    parts = norm.split()
    if len(parts) >= 2:
        last = parts[-1]
        first = parts[0]
        for db_name in db_fighters:
            db_norm = normalize_name(db_name)
            db_parts = db_norm.split()
            if len(db_parts) >= 2 and db_parts[-1] == last and db_parts[0] == first:
                return db_name
    return None
