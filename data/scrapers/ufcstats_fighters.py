"""
Scraper de peleadores desde UFCStats.com.

Recorre las páginas alfabéticas (A-Z) y extrae:
- Nombre completo
- Apodo
- Altura, peso, reach
- Stance (Orthodox/Southpaw/Switch)
- Récord (W-L-D)
- URL del perfil para scraping posterior de detalles

Uso:
    python -m data.scrapers.ufcstats_fighters
"""

from __future__ import annotations
import json
import string
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from config.settings import (
    UFCSTATS_FIGHTERS_URL,
    RAW_UFCSTATS_DIR,
    setup_logging,
)
from data.scrapers.utils import (
    ScraperClient,
    CheckpointManager,
    clean_text,
    parse_height,
    parse_reach,
    parse_weight,
    parse_record,
)

logger = setup_logging("ufcstats_fighters")

# Directorio para datos crudos de peleadores
OUTPUT_DIR = RAW_UFCSTATS_DIR / "fighters"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = RAW_UFCSTATS_DIR / "all_fighters.json"


def scrape_fighters_page(client: ScraperClient, letter: str, page: int = 1) -> list[dict]:
    """
    Scrapea una página de la lista de peleadores filtrada por letra.
    
    UFCStats tiene paginación: /statistics/fighters?char=a&page=all
    Usando page=all obtenemos todos los peleadores de esa letra en una sola página.
    """
    params = {"char": letter, "page": "all"}
    soup = client.get_soup(UFCSTATS_FIGHTERS_URL, params=params)

    fighters = []
    table = soup.find("table", class_="b-statistics__table")
    if not table:
        logger.debug(f"No se encontró tabla para letra '{letter}'")
        return fighters

    tbody = table.find("tbody")
    if not tbody:
        return fighters

    rows = tbody.find_all("tr", class_="b-statistics__table-row")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 11:
            continue

        # Columna 0: First name (con link al perfil)
        first_name_link = cols[0].find("a")
        if not first_name_link:
            continue

        profile_url = first_name_link.get("href", "").strip()
        first_name = clean_text(first_name_link.text)

        # Columna 1: Last name
        last_name = clean_text(cols[1].text)

        # Columna 2: Nickname
        nickname = clean_text(cols[2].text)

        # Columna 3: Height
        height_raw = clean_text(cols[3].text)
        height_inches = parse_height(height_raw)

        # Columna 4: Weight
        weight_raw = clean_text(cols[4].text)
        weight_lbs = parse_weight(weight_raw)

        # Columna 5: Reach
        reach_raw = clean_text(cols[5].text)
        reach_inches = parse_reach(reach_raw)

        # Columna 6: Stance
        stance = clean_text(cols[6].text) or None

        # Columna 7: Wins
        wins = clean_text(cols[7].text)

        # Columna 8: Losses
        losses = clean_text(cols[8].text)

        # Columna 9: Draws
        draws = clean_text(cols[9].text)

        # Columna 10: Belt (indicador de campeón actual o pasado)
        # A veces es una imagen, a veces está vacío
        belt_img = cols[10].find("img") if len(cols) > 10 else None
        has_belt = belt_img is not None

        full_name = f"{first_name} {last_name}".strip()

        try:
            record = {
                "wins": int(wins) if wins and wins != "--" else 0,
                "losses": int(losses) if losses and losses != "--" else 0,
                "draws": int(draws) if draws and draws != "--" else 0,
            }
        except ValueError:
            record = {"wins": 0, "losses": 0, "draws": 0}

        fighter = {
            "name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "nickname": nickname if nickname and nickname != "--" else None,
            "height_inches": height_inches,
            "weight_lbs": weight_lbs,
            "reach_inches": reach_inches,
            "stance": stance if stance and stance != "--" else None,
            "wins": record["wins"],
            "losses": record["losses"],
            "draws": record["draws"],
            "has_belt": has_belt,
            "profile_url": profile_url,
        }

        fighters.append(fighter)

    return fighters


def scrape_fighter_details(client: ScraperClient, profile_url: str) -> dict:
    """
    Scrapea el perfil individual de un peleador para obtener datos adicionales.
    
    Datos extra disponibles en el perfil:
    - Fecha de nacimiento (DOB)
    - SLpM (Significant Strikes Landed per Minute)
    - Str. Acc. (Striking Accuracy)
    - SApM (Significant Strikes Absorbed per Minute)
    - Str. Def (Strike Defense)
    - TD Avg (Takedown Average per 15 min)
    - TD Acc. (Takedown Accuracy)
    - TD Def. (Takedown Defense)
    - Sub. Avg. (Submission Average per 15 min)
    """
    soup = client.get_soup(profile_url)
    details = {}

    # Nombre completo del header
    name_el = soup.find("span", class_="b-content__title-highlight")
    if name_el:
        details["name"] = clean_text(name_el.text)

    # Record del header
    record_el = soup.find("span", class_="b-content__title-record")
    if record_el:
        record_text = clean_text(record_el.text)
        details["record"] = parse_record(record_text)

    # Info box con datos personales
    info_box = soup.find("ul", class_="b-list__box-list")
    if info_box:
        items = info_box.find_all("li", class_="b-list__box-list-item")
        for item in items:
            text = clean_text(item.text)
            if "Height:" in text:
                details["height_raw"] = text.replace("Height:", "").strip()
                details["height_inches"] = parse_height(details["height_raw"])
            elif "Weight:" in text:
                details["weight_raw"] = text.replace("Weight:", "").strip()
                details["weight_lbs"] = parse_weight(details["weight_raw"])
            elif "Reach:" in text:
                details["reach_raw"] = text.replace("Reach:", "").strip()
                details["reach_inches"] = parse_reach(details["reach_raw"])
            elif "STANCE:" in text.upper():
                details["stance"] = text.split(":")[-1].strip() or None
            elif "DOB:" in text.upper():
                dob_str = text.split(":")[-1].strip()
                details["dob"] = dob_str if dob_str and dob_str != "--" else None

    # Career statistics
    career_stats_box = soup.find_all("div", class_="b-list__info-box")
    for box in career_stats_box:
        items = box.find_all("li", class_="b-list__box-list-item")
        for item in items:
            text = clean_text(item.text)
            # Parsear stats de carrera
            stat_map = {
                "SLpM:": "slpm",
                "Str. Acc.:": "str_acc",
                "SApM:": "sapm",
                "Str. Def:": "str_def",
                "TD Avg.:": "td_avg",
                "TD Acc.:": "td_acc",
                "TD Def.:": "td_def",
                "Sub. Avg.:": "sub_avg",
            }
            for key, field in stat_map.items():
                if key in text:
                    value_str = text.split(":")[-1].strip()
                    if value_str and value_str != "--":
                        try:
                            if "%" in value_str:
                                details[field] = float(value_str.replace("%", "")) / 100
                            else:
                                details[field] = float(value_str)
                        except ValueError:
                            details[field] = None
                    else:
                        details[field] = None

    return details


def scrape_all_fighters():
    """
    Scrapea todos los peleadores de UFCStats.com recorriendo A-Z.
    
    Flujo:
    1. Recorre letras A-Z, obtiene lista básica de cada peleador
    2. Para cada peleador, visita su perfil individual para datos extra
    3. Guarda todo en all_fighters.json
    """
    checkpoint = CheckpointManager("ufcstats_fighters")
    all_fighters = []

    # Cargar datos previos si existen
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r") as f:
            all_fighters = json.load(f)
        logger.info(f"Cargados {len(all_fighters)} peleadores previos del archivo")

    with ScraperClient() as client:
        # Paso 1: Obtener lista de todos los peleadores por letra
        letters = list(string.ascii_lowercase)
        
        logger.info("=" * 60)
        logger.info("PASO 1: Scraping de lista de peleadores (A-Z)")
        logger.info("=" * 60)

        basic_fighters = []
        for letter in tqdm(letters, desc="Letras A-Z"):
            if checkpoint.is_completed(f"letter_{letter}"):
                logger.debug(f"Letra '{letter}' ya completada, saltando...")
                continue

            try:
                page_fighters = scrape_fighters_page(client, letter)
                basic_fighters.extend(page_fighters)
                checkpoint.mark_completed(f"letter_{letter}")
                logger.info(f"Letra '{letter}': {len(page_fighters)} peleadores encontrados")
            except Exception as e:
                logger.error(f"Error en letra '{letter}': {e}")
                continue

        # Combinar con datos previos (sin duplicados por URL)
        existing_urls = {f["profile_url"] for f in all_fighters}
        new_fighters = [f for f in basic_fighters if f["profile_url"] not in existing_urls]
        all_fighters.extend(new_fighters)

        logger.info(f"Total peleadores en lista: {len(all_fighters)}")
        logger.info(f"Nuevos peleadores: {len(new_fighters)}")

        # Guardar lista básica
        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_fighters, f, indent=2, ensure_ascii=False)

        # Paso 2: Obtener detalles de cada peleador
        logger.info("=" * 60)
        logger.info("PASO 2: Scraping de perfiles individuales")
        logger.info("=" * 60)

        fighters_needing_details = [
            f for f in all_fighters
            if not checkpoint.is_completed(f"detail_{f['profile_url']}")
            and f.get("profile_url")
        ]

        logger.info(f"Peleadores pendientes de detalles: {len(fighters_needing_details)}")

        for fighter in tqdm(fighters_needing_details, desc="Perfiles"):
            url = fighter["profile_url"]
            try:
                details = scrape_fighter_details(client, url)
                # Merge details into fighter dict
                fighter.update({
                    "dob": details.get("dob"),
                    "slpm": details.get("slpm"),
                    "str_acc": details.get("str_acc"),
                    "sapm": details.get("sapm"),
                    "str_def": details.get("str_def"),
                    "td_avg": details.get("td_avg"),
                    "td_acc": details.get("td_acc"),
                    "td_def": details.get("td_def"),
                    "sub_avg": details.get("sub_avg"),
                })
                checkpoint.mark_completed(f"detail_{url}")

            except Exception as e:
                logger.error(f"Error en perfil de {fighter['name']}: {e}")
                continue

            # Guardar progreso cada 50 peleadores
            if checkpoint.completed_count % 50 == 0:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(all_fighters, f, indent=2, ensure_ascii=False)

        # Guardar final
        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_fighters, f, indent=2, ensure_ascii=False)

        logger.info(f"Scraping de peleadores completado: {len(all_fighters)} total")
        logger.info(f"Datos guardados en: {OUTPUT_FILE}")

    return all_fighters


if __name__ == "__main__":
    scrape_all_fighters()
