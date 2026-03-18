"""
Utilidades compartidas para todos los scrapers.
- Cliente HTTP con reintentos y rate limiting
- Sistema de checkpoints para reanudar scraping
- Helpers de parseo comunes
"""

from __future__ import annotations
import json
import time
import random
import hashlib
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config.settings import (
    HTTP_HEADERS,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    MAX_RETRIES,
    RETRY_BACKOFF,
    REQUEST_TIMEOUT,
    CHECKPOINT_DIR,
    setup_logging,
)

logger = setup_logging("scraper_utils")


# ============================================================
# CLIENTE HTTP CON REINTENTOS
# ============================================================

class ScraperClient:
    """Cliente HTTP con rate limiting, reintentos y sesión persistente."""

    def __init__(self, delay_min: float = None, delay_max: float = None):
        self.session = requests.Session()
        self.session.headers.update(HTTP_HEADERS)
        self.delay_min = delay_min or REQUEST_DELAY_MIN
        self.delay_max = delay_max or REQUEST_DELAY_MAX
        self._last_request_time = 0

    def _wait(self):
        """Espera un tiempo aleatorio entre requests."""
        elapsed = time.time() - self._last_request_time
        delay = random.uniform(self.delay_min, self.delay_max)
        if elapsed < delay:
            time.sleep(delay - elapsed)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_BACKOFF, min=2, max=30),
        retry=retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        )),
        before_sleep=lambda retry_state: logger.warning(
            f"Reintentando request (intento {retry_state.attempt_number})..."
        ),
    )
    def get(self, url: str, params: dict = None) -> requests.Response:
        """
        GET con rate limiting y reintentos automáticos.
        Lanza excepción si el status code indica error.
        """
        self._wait()
        logger.debug(f"GET {url}")
        response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        self._last_request_time = time.time()
        response.raise_for_status()
        return response

    def get_soup(self, url: str, params: dict = None, parser: str = "lxml") -> BeautifulSoup:
        """GET y retorna BeautifulSoup parseado."""
        response = self.get(url, params=params)
        return BeautifulSoup(response.text, parser)

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ============================================================
# SISTEMA DE CHECKPOINTS
# ============================================================

class CheckpointManager:
    """
    Guarda progreso del scraping para poder reanudar si se interrumpe.
    Cada scraper tiene su propio archivo de checkpoint.
    """

    def __init__(self, scraper_name: str):
        self.name = scraper_name
        self.filepath = CHECKPOINT_DIR / f"{scraper_name}_checkpoint.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.filepath.exists():
            with open(self.filepath, "r") as f:
                return json.load(f)
        return {"completed": [], "last_index": 0, "metadata": {}}

    def save(self):
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def is_completed(self, item_id: str) -> bool:
        return item_id in self.data["completed"]

    def mark_completed(self, item_id: str, auto_save: bool = True):
        if item_id not in self.data["completed"]:
            self.data["completed"].append(item_id)
        if auto_save:
            self.save()

    def get_last_index(self) -> int:
        return self.data.get("last_index", 0)

    def set_last_index(self, index: int):
        self.data["last_index"] = index
        self.save()

    def set_metadata(self, key: str, value):
        self.data["metadata"][key] = value
        self.save()

    def get_metadata(self, key: str, default=None):
        return self.data.get("metadata", {}).get(key, default)

    @property
    def completed_count(self) -> int:
        return len(self.data["completed"])

    def reset(self):
        self.data = {"completed": [], "last_index": 0, "metadata": {}}
        self.save()


# ============================================================
# HELPERS DE PARSEO
# ============================================================

def clean_text(text: Optional[str]) -> str:
    """Limpia whitespace excesivo de texto extraído."""
    if not text:
        return ""
    return " ".join(text.strip().split())


def parse_record(record_str: str) -> dict:
    """
    Parsea un récord tipo '24-5-0' o 'Record: 24-5-0 (1 NC)'.
    Retorna dict con wins, losses, draws, no_contests.
    """
    record_str = clean_text(record_str)
    # Remover prefijo "Record:" si existe
    if ":" in record_str:
        record_str = record_str.split(":", 1)[1].strip()

    nc = 0
    if "NC" in record_str.upper():
        import re
        nc_match = re.search(r"\((\d+)\s*NC\)", record_str, re.IGNORECASE)
        if nc_match:
            nc = int(nc_match.group(1))
        record_str = re.sub(r"\(.*?\)", "", record_str).strip()

    parts = record_str.split("-")
    if len(parts) >= 3:
        return {
            "wins": int(parts[0].strip()),
            "losses": int(parts[1].strip()),
            "draws": int(parts[2].strip()),
            "no_contests": nc,
        }
    return {"wins": 0, "losses": 0, "draws": 0, "no_contests": 0}


def parse_height(height_str: str) -> Optional[float]:
    """
    Parsea altura de formato '5\\'10"' o '5\' 10"' a pulgadas totales.
    Retorna None si no se puede parsear.
    """
    import re
    height_str = clean_text(height_str)
    if not height_str or height_str == "--":
        return None

    match = re.match(r"(\d+)'\s*(\d+)\"?", height_str)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2))
        return feet * 12 + inches
    return None


def parse_reach(reach_str: str) -> Optional[float]:
    """Parsea reach de formato '72\"' o '72.0\"' a pulgadas."""
    import re
    reach_str = clean_text(reach_str)
    if not reach_str or reach_str == "--":
        return None

    match = re.match(r"([\d.]+)", reach_str)
    if match:
        return float(match.group(1))
    return None


def parse_weight(weight_str: str) -> Optional[int]:
    """Parsea peso de formato '155 lbs.' a número."""
    import re
    weight_str = clean_text(weight_str)
    if not weight_str or weight_str == "--":
        return None

    match = re.match(r"(\d+)", weight_str)
    if match:
        return int(match.group(1))
    return None


def parse_percentage(pct_str: str) -> Optional[float]:
    """Parsea porcentaje de formato '65%' a float 0.65."""
    import re
    pct_str = clean_text(pct_str)
    if not pct_str or pct_str == "--":
        return None

    match = re.match(r"([\d.]+)", pct_str)
    if match:
        return float(match.group(1)) / 100
    return None


def parse_stat_fraction(stat_str: str) -> tuple:
    """
    Parsea stats tipo '95 of 210' retornando (landed, attempted).
    """
    import re
    stat_str = clean_text(stat_str)
    if not stat_str or stat_str == "--":
        return (None, None)

    match = re.match(r"(\d+)\s*of\s*(\d+)", stat_str)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (None, None)


def parse_time(time_str: str) -> Optional[int]:
    """Parsea tiempo de formato 'M:SS' a segundos totales."""
    import re
    time_str = clean_text(time_str)
    if not time_str or time_str == "--":
        return None

    match = re.match(r"(\d+):(\d+)", time_str)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        return minutes * 60 + seconds
    return None


def generate_id(*args) -> str:
    """Genera un ID determinista basado en los argumentos dados."""
    raw = "|".join(str(a) for a in args)
    return hashlib.md5(raw.encode()).hexdigest()[:12]
