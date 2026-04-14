
from __future__ import annotations

import json
import time
import sqlite3
import re
from pathlib import Path
from datetime import datetime

from thefuzz import fuzz

KNOWN_ALIASES = {
    "patricio freire": ["patricio pitbull", "pitbull freire"]
}

def clean_name_for_match(name):
    name = name.lower().strip()
    return re.sub(r'["\']', '', name)

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# === CONFIG ===
DB_PATH = Path("db/ufc_predictor.db")
OUTPUT_DIR = Path("data/raw/sherdog")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_FILE = OUTPUT_DIR / "checkpoint.json"
RESULTS_FILE = OUTPUT_DIR / "fighter_histories.json"
ERRORS_FILE = OUTPUT_DIR / "errors.json"

DELAY = 2.0  # Segundos entre requests (ser respetuoso)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

session = requests.Session()
session.headers.update(HEADERS)


def get_active_fighters():
    """Obtener lista de peleadores activos (pelea en 2024+) de la BD."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT DISTINCT f.name, f.wins, f.losses, f.draws
        FROM fighters f
        WHERE f.name IN (
            SELECT fighter_a_name FROM fights fi
            JOIN events e ON fi.event_id = e.event_id
            WHERE e.date_parsed >= '2024-01-01'
            UNION
            SELECT fighter_b_name FROM fights fi
            JOIN events e ON fi.event_id = e.event_id
            WHERE e.date_parsed >= '2024-01-01'
        )
        ORDER BY f.name
    """).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def search_fighter(name):
    try:
        name_clean = clean_name_for_match(name)
        search_query = KNOWN_ALIASES.get(name_clean, [name])[0]

        url = "https://www.sherdog.com/stats/fightfinder"
        params = {"SearchTxt": search_query}
        r = session.get(url, params=params, timeout=15)

        if r.status_code != 200: return None

        soup = BeautifulSoup(r.text, "lxml")

        valid_names = [name_clean]
        if name_clean in KNOWN_ALIASES:
            valid_names.extend(KNOWN_ALIASES[name_clean])

        best_match = None
        best_score = 0

        for a in soup.find_all("a"):
            href = a.get("href", "")
            if "/fighter/" not in href: continue

            link_text = clean_name_for_match(a.text)
            if not link_text: continue

            for valid_name in valid_names:
                score = fuzz.token_set_ratio(valid_name, link_text)
                if score > best_score:
                    best_score = score
                    best_match = "https://www.sherdog.com" + href if href.startswith("/") else href
                
                if best_score == 100: break
            if best_score == 100: break

        if best_score >= 85:
            return best_match

        return None
    except Exception:
        return None


def scrape_fighter_profile(profile_url):
    """Scrapear perfil completo de un peleador en Sherdog."""
    try:
        r = session.get(profile_url, timeout=15)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        tables = soup.find_all("table")

        if len(tables) < 2:
            return None

        # Tabla 0: Info del peleador
        info = {}
        for row in tables[0].find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                key = cells[0].text.strip().upper()
                val = cells[1].text.strip()
                if "AGE" in key:
                    info["age_str"] = val
                elif "HEIGHT" in key:
                    info["height"] = val
                elif "WEIGHT" in key:
                    info["weight"] = val
                elif "CLASS" in key:
                    info["weight_class"] = val
                elif "BIRTH" in key or "BORN" in key:
                    info["birthplace"] = val
                elif "ASSOCIATION" in key or "TEAM" in key:
                    info["team"] = val

        # Tabla 1: Historial de peleas
        fights = []
        fight_table = tables[1]
        rows = fight_table.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            result = cells[0].text.strip().lower()
            opponent = cells[1].text.strip()
            event = cells[2].text.strip()
            method_full = cells[3].text.strip()
            rnd = cells[4].text.strip()
            time_str = cells[5].text.strip()

            # Parsear metodo
            method = method_full.split("\n")[0].strip() if method_full else ""

            # Detectar si es pelea UFC
            is_ufc = "ufc" in event.lower()

            # Extraer fecha del evento si esta disponible
            date_match = re.search(r'(\w+ \d{1,2}, \d{4})', event)
            fight_date = date_match.group(1) if date_match else None

            # Limpiar evento - extraer fecha separada
            event_links = cells[2].find_all("a")
            event_name = event_links[0].text.strip() if event_links else event.split("\n")[0].strip()

            # Fecha puede estar como texto despues del nombre del evento
            event_text_parts = cells[2].get_text(separator="\n").strip().split("\n")
            event_name = event_text_parts[0].strip() if event_text_parts else event
            if len(event_text_parts) > 1:
                for part in event_text_parts[1:]:
                    part = part.strip()
                    dm = re.search(r'(\w+ / \d{1,2}, \d{4}|\w+ \d{1,2}, \d{4}|\d{4})', part)
                    if dm:
                        fight_date = part.strip()
                        break

            fights.append({
                "result": result,
                "opponent": opponent,
                "event": event_name[:100],
                "method": method[:80],
                "round": rnd,
                "time": time_str,
                "is_ufc": is_ufc,
                "date": fight_date,
            })

        return {
            "info": info,
            "fights": fights,
            "total_fights": len(fights),
            "pre_ufc_fights": sum(1 for f in fights if not f["is_ufc"]),
            "ufc_fights": sum(1 for f in fights if f["is_ufc"]),
            "url": profile_url,
        }

    except Exception as e:
        return None


def load_checkpoint():
    """Cargar checkpoint de progreso."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"completed": [], "results": {}, "errors": {}}


def save_checkpoint(checkpoint):
    """Guardar checkpoint."""
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False)


def main():
    print("=" * 60)
    print("SHERDOG SCRAPER - Historial Completo de Peleadores")
    print("=" * 60)

    # Obtener peleadores activos
    print("\nCargando peleadores activos de la BD...")
    fighters = get_active_fighters()
    print("Peleadores activos (2024+):", len(fighters))

    # Cargar checkpoint
    checkpoint = load_checkpoint()
    completed = set(checkpoint["completed"])
    results = checkpoint["results"]
    errors = checkpoint["errors"]

    remaining = [f for f in fighters if f["name"] not in completed]
    print("Ya completados:", len(completed))
    print("Pendientes:", len(remaining))

    if not remaining:
        print("\nTodos los peleadores ya fueron scrapeados!")
    else:
        print("\nIniciando scraping...")
        print("Delay entre requests:", DELAY, "segundos")
        print("Tiempo estimado:", round(len(remaining) * DELAY * 2 / 60, 0), "minutos")
        print()

    found = 0
    not_found = 0
    with_pre_ufc = 0

    for fighter in tqdm(remaining, desc="Scraping"):
        name = fighter["name"]

        try:
            # Paso 1: Buscar en Sherdog
            profile_url = search_fighter(name)
            time.sleep(DELAY)

            if not profile_url:
                errors[name] = "No encontrado en busqueda"
                not_found += 1
                completed.add(name)
                if len(completed) % 50 == 0:
                    save_checkpoint({"completed": list(completed), "results": results, "errors": errors})
                continue

            # Paso 2: Scrapear perfil
            profile = scrape_fighter_profile(profile_url)
            time.sleep(DELAY)

            if not profile:
                errors[name] = "Error scrapeando perfil: " + profile_url
                not_found += 1
                completed.add(name)
                continue

            # Guardar resultado
            results[name] = profile
            found += 1

            if profile["pre_ufc_fights"] > 0:
                with_pre_ufc += 1

            completed.add(name)

            # Checkpoint cada 50 peleadores
            if len(completed) % 50 == 0:
                save_checkpoint({"completed": list(completed), "results": results, "errors": errors})
                tqdm.write(f"  Checkpoint: {len(completed)}/{len(fighters)} | "
                          f"Found: {found} | Pre-UFC: {with_pre_ufc} | Not found: {not_found}")

        except KeyboardInterrupt:
            print("\n\nInterrumpido! Guardando checkpoint...")
            save_checkpoint({"completed": list(completed), "results": results, "errors": errors})
            print("Checkpoint guardado. Ejecuta de nuevo para continuar.")
            return

        except Exception as e:
            errors[name] = str(e)
            completed.add(name)

    # Guardar final
    save_checkpoint({"completed": list(completed), "results": results, "errors": errors})

    # Guardar resultados limpios
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Guardar errores
    with open(ERRORS_FILE, "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)

    # Resumen
    total_pre_ufc = sum(r["pre_ufc_fights"] for r in results.values())
    print("\n" + "=" * 60)
    print("COMPLETADO")
    print("=" * 60)
    print(f"  Peleadores buscados:    {len(fighters)}")
    print(f"  Encontrados en Sherdog: {len(results)}")
    print(f"  No encontrados:         {len(errors)}")
    print(f"  Con peleas pre-UFC:     {with_pre_ufc}")
    print(f"  Total peleas pre-UFC:   {total_pre_ufc}")
    print(f"\n  Guardado en: {RESULTS_FILE}")
    print(f"  Errores en:  {ERRORS_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()