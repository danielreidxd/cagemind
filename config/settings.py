"""
Configuración global del proyecto UFC Fight Predictor.
Rutas, constantes, headers HTTP y configuración de logging.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
DB_DIR = PROJECT_ROOT / "db"
LOGS_DIR = PROJECT_ROOT / "logs"

# Crear directorios si no existen
for d in [RAW_DIR, PROCESSED_DIR, EXPORTS_DIR, DB_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Subdirectorios de datos crudos
RAW_UFCSTATS_DIR = RAW_DIR / "ufcstats"
RAW_UFCSTATS_DIR.mkdir(parents=True, exist_ok=True)

# Base de datos
DB_PATH = DB_DIR / "ufc_predictor.db"

# Checkpoints (para reanudar scraping interrumpido)
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# CONFIGURACIÓN DE SCRAPING
# ============================================================

# Headers para simular un navegador real
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

# Delays entre requests (segundos) — sé respetuoso con los servidores
REQUEST_DELAY_MIN = 1.0
REQUEST_DELAY_MAX = 2.5

# Reintentos en caso de fallo
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # Multiplicador exponencial entre reintentos

# Timeout para requests HTTP (segundos)
REQUEST_TIMEOUT = 30

# ============================================================
# URLs BASE
# ============================================================

UFCSTATS_BASE_URL = "http://www.ufcstats.com"
UFCSTATS_FIGHTERS_URL = f"{UFCSTATS_BASE_URL}/statistics/fighters"
UFCSTATS_EVENTS_URL = f"{UFCSTATS_BASE_URL}/statistics/events/completed"
UFCSTATS_EVENT_DETAILS_URL = f"{UFCSTATS_BASE_URL}/event-details/"
UFCSTATS_FIGHT_DETAILS_URL = f"{UFCSTATS_BASE_URL}/fight-details/"

# ============================================================
# LOGGING
# ============================================================

def setup_logging(name: str = "ufc_predictor") -> logging.Logger:
    """Configura logging con salida a archivo y consola."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Evitar handlers duplicados
    if logger.handlers:
        return logger

    # Formato
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler de archivo
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = LOGS_DIR / f"{name}_{timestamp}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Handler de consola
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


# ============================================================
# CONSTANTES DE CATEGORÍAS DE PESO
# ============================================================

WEIGHT_CLASSES = {
    "Strawweight": 115,
    "Flyweight": 125,
    "Bantamweight": 135,
    "Featherweight": 145,
    "Lightweight": 155,
    "Welterweight": 170,
    "Middleweight": 185,
    "Light Heavyweight": 205,
    "Heavyweight": 265,
    "Women's Strawweight": 115,
    "Women's Flyweight": 125,
    "Women's Bantamweight": 135,
    "Women's Featherweight": 145,
}
