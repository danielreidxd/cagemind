"""
Scraper de eventos y peleas desde UFCStats.com.

Recorre la lista de todos los eventos completados y para cada uno extrae:
- Nombre del evento, fecha, ubicación
- Lista de peleas con: peleadores, resultado, método, round, tiempo

Uso:
    python -m data.scrapers.ufcstats_events
"""

from __future__ import annotations
import json
import re
from pathlib import Path

from tqdm import tqdm

from config.settings import (
    UFCSTATS_EVENTS_URL,
    RAW_UFCSTATS_DIR,
    setup_logging,
)
from data.scrapers.utils import (
    ScraperClient,
    CheckpointManager,
    clean_text,
    parse_time,
    generate_id,
)

logger = setup_logging("ufcstats_events")

OUTPUT_EVENTS_FILE = RAW_UFCSTATS_DIR / "all_events.json"
OUTPUT_FIGHTS_FILE = RAW_UFCSTATS_DIR / "all_fights.json"


def scrape_events_list(client: ScraperClient) -> list[dict]:
    """
    Scrapea la lista completa de eventos desde la página paginada.
    UFCStats permite page=all para obtener todos.
    """
    params = {"page": "all"}
    soup = client.get_soup(UFCSTATS_EVENTS_URL, params=params)

    events = []
    table = soup.find("table", class_="b-statistics__table-events")
    if not table:
        logger.error("No se encontró la tabla de eventos")
        return events

    tbody = table.find("tbody")
    if not tbody:
        return events

    rows = tbody.find_all("tr", class_="b-statistics__table-row")

    for row in rows:
        link = row.find("a", class_="b-link")
        if not link:
            continue

        event_url = link.get("href", "").strip()
        event_name = clean_text(link.text)

        # Fecha del evento
        date_col = row.find("span", class_="b-statistics__date")
        event_date = clean_text(date_col.text) if date_col else None

        # Ubicación
        location_td = row.find_all("td")
        event_location = None
        if len(location_td) >= 2:
            event_location = clean_text(location_td[-1].text) or None

        if not event_name or not event_url:
            continue

        events.append({
            "event_id": generate_id(event_name, event_date),
            "name": event_name,
            "date": event_date,
            "location": event_location,
            "url": event_url,
            "organization": "UFC",
        })

    return events


def scrape_event_fights(client: ScraperClient, event_url: str, event_id: str) -> list[dict]:
    """
    Scrapea todas las peleas de un evento específico.
    
    Cada pelea incluye:
    - Peleadores (fighter_a, fighter_b)
    - Ganador (o draw/no contest)
    - Método de victoria
    - Round y tiempo de finalización
    - Categoría de peso
    - URL de detalles de la pelea (para stats round-by-round)
    """
    soup = client.get_soup(event_url)
    fights = []

    fight_rows = soup.find_all("tr", class_="b-fight-details__table-row")

    for row in fight_rows:
        # Link a detalles de la pelea
        link_attr = row.get("data-link", "")
        if not link_attr:
            # Intentar encontrar en la primera columna
            first_td = row.find("td")
            if first_td:
                a_tag = first_td.find("a")
                if a_tag:
                    link_attr = a_tag.get("href", "")

        if not link_attr:
            continue

        cols = row.find_all("td")
        if len(cols) < 10:
            continue

        # Columna 0: Win/Loss/Draw/NC indicator
        result_col = cols[0]
        result_text = clean_text(result_col.text)
        # "win" indica que el fighter_a ganó, "loss" que perdió, etc.

        # Columna 1: Peleadores (ambos nombres apilados)
        fighters_col = cols[1]
        fighter_links = fighters_col.find_all("a")
        if len(fighter_links) < 2:
            fighter_ps = fighters_col.find_all("p")
            if len(fighter_ps) < 2:
                continue
            fighter_a_name = clean_text(fighter_ps[0].text)
            fighter_b_name = clean_text(fighter_ps[1].text)
            fighter_a_url = None
            fighter_b_url = None
        else:
            fighter_a_name = clean_text(fighter_links[0].text)
            fighter_b_name = clean_text(fighter_links[1].text)
            fighter_a_url = fighter_links[0].get("href", "").strip()
            fighter_b_url = fighter_links[1].get("href", "").strip()

        # Columna 2: KD (knockdowns) — aparecen 2 valores apilados
        # Columna 3: STR (significant strikes) — 2 valores apilados
        # Columna 4: TD (takedowns) — 2 valores apilados
        # Columna 5: SUB (submission attempts) — 2 valores apilados

        # Columna 6: Weight class
        weight_class = clean_text(cols[6].text) if len(cols) > 6 else None

        # Columna 7: Method
        method_col = cols[7] if len(cols) > 7 else None
        method = clean_text(method_col.text) if method_col else None

        # Columna 8: Round
        round_col = cols[8] if len(cols) > 8 else None
        fight_round = clean_text(round_col.text) if round_col else None

        # Columna 9: Time
        time_col = cols[9] if len(cols) > 9 else None
        fight_time = clean_text(time_col.text) if time_col else None

        # Determinar ganador
        # En UFCStats, el primer peleador listado con "win" ganó
        win_indicators = result_col.find_all("i")
        winner = None
        is_draw = False
        is_nc = False

        if win_indicators:
            for indicator in win_indicators:
                icon_class = indicator.get("class", [])
                icon_text = clean_text(indicator.text).lower()
                if "win" in icon_text:
                    winner = fighter_a_name
                    break
                elif "draw" in icon_text:
                    is_draw = True
                    break
                elif "nc" in icon_text:
                    is_nc = True
                    break
        else:
            # Fallback: si "W" o "win" está en el texto
            if result_text.lower().startswith("w"):
                winner = fighter_a_name

        # Si no se determinó ganador y no es draw/nc, el primer peleador ganó
        # (UFCStats lista al ganador primero por defecto)
        if not winner and not is_draw and not is_nc and method:
            winner = fighter_a_name

        try:
            round_num = int(fight_round) if fight_round else None
        except ValueError:
            round_num = None

        time_seconds = parse_time(fight_time) if fight_time else None

        fight = {
            "fight_id": generate_id(fighter_a_name, fighter_b_name, event_id),
            "event_id": event_id,
            "fighter_a": fighter_a_name,
            "fighter_b": fighter_b_name,
            "fighter_a_url": fighter_a_url,
            "fighter_b_url": fighter_b_url,
            "winner": winner,
            "is_draw": is_draw,
            "is_no_contest": is_nc,
            "method": method,
            "method_detail": None,  # Se llenará al scrapear detalles
            "round": round_num,
            "time": fight_time,
            "time_seconds": time_seconds,
            "weight_class": weight_class,
            "fight_details_url": link_attr,
        }

        fights.append(fight)

    return fights


def scrape_all_events():
    """
    Scrapea todos los eventos y sus peleas.
    
    Flujo:
    1. Obtener lista de todos los eventos
    2. Para cada evento, scrapear la lista de peleas
    """
    checkpoint = CheckpointManager("ufcstats_events")
    all_events = []
    all_fights = []

    # Cargar datos previos si existen
    if OUTPUT_EVENTS_FILE.exists():
        with open(OUTPUT_EVENTS_FILE, "r") as f:
            all_events = json.load(f)

    if OUTPUT_FIGHTS_FILE.exists():
        with open(OUTPUT_FIGHTS_FILE, "r") as f:
            all_fights = json.load(f)

    with ScraperClient() as client:
        # Paso 1: Lista de eventos
        if not checkpoint.is_completed("events_list"):
            logger.info("=" * 60)
            logger.info("PASO 1: Scraping de lista de eventos")
            logger.info("=" * 60)

            events = scrape_events_list(client)
            # Merge sin duplicados
            existing_ids = {e["event_id"] for e in all_events}
            new_events = [e for e in events if e["event_id"] not in existing_ids]
            all_events.extend(new_events)

            with open(OUTPUT_EVENTS_FILE, "w") as f:
                json.dump(all_events, f, indent=2, ensure_ascii=False)

            checkpoint.mark_completed("events_list")
            logger.info(f"Total eventos: {len(all_events)}")

        # Paso 2: Peleas por evento
        logger.info("=" * 60)
        logger.info("PASO 2: Scraping de peleas por evento")
        logger.info("=" * 60)

        events_pending = [
            e for e in all_events
            if not checkpoint.is_completed(f"event_{e['event_id']}")
            and e.get("url")
        ]
        logger.info(f"Eventos pendientes: {len(events_pending)}")

        for event in tqdm(events_pending, desc="Eventos"):
            try:
                event_fights = scrape_event_fights(
                    client, event["url"], event["event_id"]
                )
                all_fights.extend(event_fights)
                checkpoint.mark_completed(f"event_{event['event_id']}")

                logger.info(
                    f"  {event['name']}: {len(event_fights)} peleas"
                )

            except Exception as e:
                logger.error(f"Error en evento {event['name']}: {e}")
                continue

            # Guardar progreso cada 20 eventos
            if checkpoint.completed_count % 20 == 0:
                with open(OUTPUT_FIGHTS_FILE, "w") as f:
                    json.dump(all_fights, f, indent=2, ensure_ascii=False)

        # Guardar final
        with open(OUTPUT_FIGHTS_FILE, "w") as f:
            json.dump(all_fights, f, indent=2, ensure_ascii=False)

        logger.info(f"Scraping de eventos completado: {len(all_events)} eventos, {len(all_fights)} peleas")

    return all_events, all_fights


if __name__ == "__main__":
    scrape_all_events()
