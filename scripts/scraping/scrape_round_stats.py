
from __future__ import annotations

import json
import time
import random
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ============================================================
# CONFIGURACIÓN
# ============================================================

PROJECT_ROOT = Path(__file__).parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "ufcstats"
DB_PATH = PROJECT_ROOT / "db" / "ufc_predictor.db"
CHECKPOINT_DIR = PROJECT_ROOT / "data" / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

FIGHTS_FILE = RAW_DIR / "all_fights.json"
OUTPUT_FILE = RAW_DIR / "all_round_stats.json"
CHECKPOINT_FILE = CHECKPOINT_DIR / "round_stats_checkpoint.json"

# Rate limiting
DELAY_MIN = 1.0
DELAY_MAX = 2.5
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    if not text:
        return ""
    return " ".join(text.strip().split())


def parse_stat_fraction(stat_str):
    """Parsea '95 of 210' → (95, 210)"""
    import re
    stat_str = clean_text(stat_str)
    if not stat_str or stat_str == "--":
        return (None, None)
    match = re.match(r"(\d+)\s*of\s*(\d+)", stat_str)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (None, None)


def parse_time(time_str):
    """Parsea 'M:SS' → segundos"""
    import re
    time_str = clean_text(time_str)
    if not time_str or time_str == "--":
        return None
    match = re.match(r"(\d+):(\d+)", time_str)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return None


def safe_int(v):
    try:
        return int(v) if v and v != "--" else None
    except (ValueError, TypeError):
        return None


def parse_table_rows(table):
    """Parsea filas de tabla UFCStats. Cada celda tiene 2 <p> (fighter A y B)."""
    tbody = table.find("tbody")
    if not tbody:
        return []
    rows_data = []
    for row in tbody.find_all("tr"):
        cols = row.find_all("td")
        row_vals = []
        for col in cols:
            ps = col.find_all("p")
            if len(ps) >= 2:
                row_vals.append((clean_text(ps[0].text), clean_text(ps[1].text)))
            else:
                text = clean_text(col.text)
                row_vals.append((text, None))
        rows_data.append(row_vals)
    return rows_data


# ============================================================
# CHECKPOINT
# ============================================================

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"completed": set()}


def save_checkpoint(data):
    # Convert set to list for JSON
    serializable = {"completed": list(data["completed"])}
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(serializable, f)


# ============================================================
# SCRAPER PRINCIPAL
# ============================================================

def scrape_fight_rounds(session, fight_url):
    """
    Scrapea las tablas round-by-round de una pelea.
    
    Busca las 4 tablas y captura específicamente las de clase 'js-fight-table'
    (Tabla 1 = totals por round, Tabla 3 = sig strikes por round).
    
    Returns: dict con 'totals_by_round' y 'sig_strikes_by_round'
    """
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(fight_url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            break
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    
    soup = BeautifulSoup(resp.text, "lxml")
    result = {
        "totals_by_round": [],
        "sig_strikes_by_round": [],
    }
    
    # Buscar TODAS las tablas
    tables = soup.find_all("table")
    
    # Clasificar las 4 tablas por headers y clase CSS
    # Necesitamos las tablas CON clase 'js-fight-table' (las de rounds)
    totals_round_table = None
    sig_strikes_round_table = None
    
    for table in tables:
        thead = table.find("thead")
        if not thead:
            continue
        
        headers = [clean_text(th.text).lower() for th in thead.find_all("th")]
        header_str = " ".join(headers)
        is_round_table = "js-fight-table" in (table.get("class", []) or [])
        # Alternativa: la tabla de rounds es la SEGUNDA que matchea cada categoría
        
        if "ctrl" in header_str:
            if is_round_table:
                totals_round_table = table
            # Si no es js-fight-table, es la tabla resumen (ya capturada)
        
        elif "head" in header_str and "body" in header_str:
            if is_round_table:
                sig_strikes_round_table = table
    
    # Si no encontramos por clase CSS, intentar por orden:
    # Las tablas de rounds son la 2da y 4ta tabla con esos headers
    if totals_round_table is None or sig_strikes_round_table is None:
        totals_tables = []
        sig_tables = []
        
        for table in tables:
            thead = table.find("thead")
            if not thead:
                continue
            headers = [clean_text(th.text).lower() for th in thead.find_all("th")]
            header_str = " ".join(headers)
            
            if "ctrl" in header_str:
                totals_tables.append(table)
            elif "head" in header_str and "body" in header_str:
                sig_tables.append(table)
        
        # La primera es resumen, la segunda es por round
        if len(totals_tables) >= 2 and totals_round_table is None:
            totals_round_table = totals_tables[1]
        if len(sig_tables) >= 2 and sig_strikes_round_table is None:
            sig_strikes_round_table = sig_tables[1]
    
    # ===== PARSEAR TOTALS POR ROUND =====
    if totals_round_table:
        rows_data = parse_table_rows(totals_round_table)
        for round_idx, row_vals in enumerate(rows_data):
            if len(row_vals) < 10:
                continue
            
            fighter_a = row_vals[0][0]
            fighter_b = row_vals[0][1]
            kd_a, kd_b = row_vals[1]
            sig_str_a, sig_str_b = row_vals[2]
            sig_pct_a, sig_pct_b = row_vals[3]
            total_str_a, total_str_b = row_vals[4]
            td_a, td_b = row_vals[5]
            td_pct_a, td_pct_b = row_vals[6]
            sub_a, sub_b = row_vals[7]
            rev_a, rev_b = row_vals[8]
            ctrl_a, ctrl_b = row_vals[9]
            
            sig_landed_a, sig_att_a = parse_stat_fraction(sig_str_a)
            sig_landed_b, sig_att_b = parse_stat_fraction(sig_str_b)
            total_landed_a, total_att_a = parse_stat_fraction(total_str_a)
            total_landed_b, total_att_b = parse_stat_fraction(total_str_b)
            td_landed_a, td_att_a = parse_stat_fraction(td_a)
            td_landed_b, td_att_b = parse_stat_fraction(td_b)
            
            round_data = {
                "round": round_idx + 1,
                "fighter_a": fighter_a,
                "fighter_b": fighter_b,
                "fighter_a_stats": {
                    "knockdowns": safe_int(kd_a),
                    "sig_strikes_landed": sig_landed_a,
                    "sig_strikes_attempted": sig_att_a,
                    "sig_strike_pct": sig_pct_a,
                    "total_strikes_landed": total_landed_a,
                    "total_strikes_attempted": total_att_a,
                    "takedowns_landed": td_landed_a,
                    "takedowns_attempted": td_att_a,
                    "takedown_pct": td_pct_a,
                    "submission_attempts": safe_int(sub_a),
                    "reversals": safe_int(rev_a),
                    "control_time": ctrl_a,
                    "control_time_seconds": parse_time(ctrl_a),
                },
                "fighter_b_stats": {
                    "knockdowns": safe_int(kd_b),
                    "sig_strikes_landed": sig_landed_b,
                    "sig_strikes_attempted": sig_att_b,
                    "sig_strike_pct": sig_pct_b,
                    "total_strikes_landed": total_landed_b,
                    "total_strikes_attempted": total_att_b,
                    "takedowns_landed": td_landed_b,
                    "takedowns_attempted": td_att_b,
                    "takedown_pct": td_pct_b,
                    "submission_attempts": safe_int(sub_b),
                    "reversals": safe_int(rev_b),
                    "control_time": ctrl_b,
                    "control_time_seconds": parse_time(ctrl_b),
                },
            }
            result["totals_by_round"].append(round_data)
    
    # ===== PARSEAR SIG STRIKES POR ROUND =====
    if sig_strikes_round_table:
        rows_data = parse_table_rows(sig_strikes_round_table)
        for round_idx, row_vals in enumerate(rows_data):
            if len(row_vals) < 9:
                continue
            
            fighter_a = row_vals[0][0]
            fighter_b = row_vals[0][1]
            head_a, head_b = row_vals[3]
            body_a, body_b = row_vals[4]
            leg_a, leg_b = row_vals[5]
            dist_a, dist_b = row_vals[6]
            clinch_a, clinch_b = row_vals[7]
            ground_a, ground_b = row_vals[8]
            
            head_l_a, head_att_a = parse_stat_fraction(head_a)
            head_l_b, head_att_b = parse_stat_fraction(head_b)
            body_l_a, body_att_a = parse_stat_fraction(body_a)
            body_l_b, body_att_b = parse_stat_fraction(body_b)
            leg_l_a, leg_att_a = parse_stat_fraction(leg_a)
            leg_l_b, leg_att_b = parse_stat_fraction(leg_b)
            dist_l_a, dist_att_a = parse_stat_fraction(dist_a)
            dist_l_b, dist_att_b = parse_stat_fraction(dist_b)
            clinch_l_a, clinch_att_a = parse_stat_fraction(clinch_a)
            clinch_l_b, clinch_att_b = parse_stat_fraction(clinch_b)
            ground_l_a, ground_att_a = parse_stat_fraction(ground_a)
            ground_l_b, ground_att_b = parse_stat_fraction(ground_b)
            
            sig_data = {
                "round": round_idx + 1,
                "fighter_a": fighter_a,
                "fighter_b": fighter_b,
                "fighter_a_strikes": {
                    "head_landed": head_l_a, "head_attempted": head_att_a,
                    "body_landed": body_l_a, "body_attempted": body_att_a,
                    "leg_landed": leg_l_a, "leg_attempted": leg_att_a,
                    "distance_landed": dist_l_a, "distance_attempted": dist_att_a,
                    "clinch_landed": clinch_l_a, "clinch_attempted": clinch_att_a,
                    "ground_landed": ground_l_a, "ground_attempted": ground_att_a,
                },
                "fighter_b_strikes": {
                    "head_landed": head_l_b, "head_attempted": head_att_b,
                    "body_landed": body_l_b, "body_attempted": body_att_b,
                    "leg_landed": leg_l_b, "leg_attempted": leg_att_b,
                    "distance_landed": dist_l_b, "distance_attempted": dist_att_b,
                    "clinch_landed": clinch_l_b, "clinch_attempted": clinch_att_b,
                    "ground_landed": ground_l_b, "ground_attempted": ground_att_b,
                },
            }
            result["sig_strikes_by_round"].append(sig_data)
    
    return result


def main():
    print("=" * 60)
    print("CAGEMIND — SCRAPER DE ESTADÍSTICAS ROUND-BY-ROUND")
    print("=" * 60)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Cargar peleas
    if not FIGHTS_FILE.exists():
        print(f"ERROR: No se encontró {FIGHTS_FILE}")
        print("Ejecuta primero el scraper de peleas.")
        return
    
    with open(FIGHTS_FILE) as f:
        all_fights = json.load(f)
    print(f"Total peleas: {len(all_fights)}")
    
    # Cargar stats previas (para append)
    all_round_stats = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
        # Convertir lista a dict por fight_id
        if isinstance(existing, list):
            for item in existing:
                all_round_stats[item["fight_id"]] = item
        elif isinstance(existing, dict):
            all_round_stats = existing
        print(f"Stats round-by-round previas: {len(all_round_stats)}")
    
    # Checkpoint
    checkpoint = load_checkpoint()
    completed = set(checkpoint.get("completed", []))
    print(f"Checkpoint: {len(completed)} peleas completadas previamente")
    
    # Filtrar pendientes
    fights_pending = [
        f for f in all_fights
        if f.get("fight_details_url")
        and f["fight_id"] not in completed
    ]
    print(f"Peleas pendientes: {len(fights_pending)}")
    
    if not fights_pending:
        print("¡Todas las peleas ya están scrapeadas!")
        return
    
    # Estimar tiempo
    avg_seconds = (DELAY_MIN + DELAY_MAX) / 2 + 0.5  # delay + request time
    est_hours = len(fights_pending) * avg_seconds / 3600
    print(f"Tiempo estimado: ~{est_hours:.1f} horas")
    print()
    
    # Scraping
    session = requests.Session()
    session.headers.update(HEADERS)
    
    errors = 0
    start_time = time.time()
    
    try:
        for i, fight in enumerate(tqdm(fights_pending, desc="Round Stats")):
            url = fight["fight_details_url"]
            fight_id = fight["fight_id"]
            
            try:
                round_data = scrape_fight_rounds(session, url)
                round_data["fight_id"] = fight_id
                round_data["fight_url"] = url
                round_data["fighter_a"] = fight["fighter_a"]
                round_data["fighter_b"] = fight["fighter_b"]
                round_data["event_id"] = fight["event_id"]
                
                all_round_stats[fight_id] = round_data
                completed.add(fight_id)
                
            except Exception as e:
                errors += 1
                tqdm.write(f"  ERROR {fight['fighter_a']} vs {fight['fighter_b']}: {e}")
                continue
            
            # Guardar progreso cada 100 peleas
            if (i + 1) % 100 == 0:
                # Guardar JSON
                stats_list = list(all_round_stats.values())
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(stats_list, f, ensure_ascii=False)
                
                # Guardar checkpoint
                save_checkpoint({"completed": completed})
                
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed
                remaining = (len(fights_pending) - i - 1) / speed
                tqdm.write(
                    f"  Guardado: {len(all_round_stats)} peleas | "
                    f"Errores: {errors} | "
                    f"Restante: ~{remaining/3600:.1f}h"
                )
    
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario. Guardando progreso...")
    
    finally:
        # Guardar final
        stats_list = list(all_round_stats.values())
        with open(OUTPUT_FILE, "w") as f:
            json.dump(stats_list, f, ensure_ascii=False)
        save_checkpoint({"completed": completed})
        
        elapsed = time.time() - start_time
        
        print()
        print("=" * 60)
        print("RESUMEN")
        print("=" * 60)
        print(f"Peleas scrapeadas: {len(completed)}")
        print(f"Errores: {errors}")
        print(f"Tiempo: {elapsed/3600:.1f} horas")
        print(f"Archivo: {OUTPUT_FILE}")
        print(f"Checkpoint: {CHECKPOINT_FILE}")
        
        # Stats de validación
        multi_round = sum(
            1 for s in all_round_stats.values()
            if len(s.get("totals_by_round", [])) > 1
        )
        single_round = sum(
            1 for s in all_round_stats.values()
            if len(s.get("totals_by_round", [])) == 1
        )
        no_rounds = sum(
            1 for s in all_round_stats.values()
            if len(s.get("totals_by_round", [])) == 0
        )
        print(f"\nValidación:")
        print(f"  Peleas multi-round: {multi_round}")
        print(f"  Peleas 1 round (KO/Sub R1): {single_round}")
        print(f"  Peleas sin datos: {no_rounds}")
    
    session.close()


if __name__ == "__main__":
    main()
