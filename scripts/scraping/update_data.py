"""
CageMind — Actualización Automática de Datos

Dos modos de ejecución:
  1. --upcoming  : Scrapea carteleras futuras (rápido, ~1 min)
  2. --post-event: Scrapea resultados + stats + perfiles del último evento (~5-10 min)

GitHub Actions corre:
  - --upcoming cada 2 días
  - --post-event los lunes

Uso:
    python update_data.py --upcoming
    python update_data.py --post-event
    python update_data.py --all          (ambos)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURACIÓN
# ============================================================
DB_PATH = Path("db/ufc_predictor.db")
UPCOMING_FILE = Path("data/raw/ufcstats/upcoming_events.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def clean(text):
    if not text:
        return ""
    return " ".join(text.strip().split())


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")


def generate_id(*parts):
    """Genera un ID determinístico basado en los datos (misma lógica que utils.py)."""
    combined = "_".join(str(p) for p in parts if p)
    return hashlib.md5(combined.encode()).hexdigest()[:12]


def normalize_name(name):
    if not name:
        return ""
    return re.sub(r"\s+", " ", name.strip().lower())


def get_db():
    """Obtiene conexión a la BD."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def parse_date_ufcstats(date_str):
    """Parsea fecha de UFCStats a YYYY-MM-DD."""
    if not date_str or date_str.strip() == "--":
        return None
    date_str = date_str.strip()
    for fmt in ["%B %d, %Y", "%b %d, %Y", "%b. %d, %Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_stat_fraction(text):
    """Parsea '45 of 90' o '45/90' a (45, 90)."""
    if not text:
        return (None, None)
    text = text.strip()
    match = re.match(r"(\d+)\s*(?:of|/)\s*(\d+)", text)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (None, None)


def parse_time_to_seconds(text):
    """Parsea '4:35' a 275 segundos."""
    if not text or text == "--":
        return None
    match = re.match(r"(\d+):(\d+)", text.strip())
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return None


def safe_int(v):
    try:
        return int(v) if v and v != "--" else None
    except (ValueError, TypeError):
        return None


# ============================================================
# PARTE 1: UPCOMING EVENTS
# ============================================================
def update_upcoming():
    """Scrapea carteleras futuras desde UFCStats.com."""
    log("📅 Scrapeando eventos upcoming...")

    url = "http://www.ufcstats.com/statistics/events/upcoming"
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    events = []
    table = soup.find("table", class_="b-statistics__table-events")
    if not table:
        log("  No se encontró tabla de eventos")
        return []

    tbody = table.find("tbody")
    if not tbody:
        return []

    rows = tbody.find_all("tr", class_="b-statistics__table-row")

    for row in rows:
        link = row.find("a", class_="b-link")
        if not link:
            continue

        name = clean(link.text)
        href = link.get("href", "").strip()
        date_span = row.find("span", class_="b-statistics__date")
        date = clean(date_span.text) if date_span else None

        tds = row.find_all("td")
        location = clean(tds[-1].text) if len(tds) > 1 else None

        if name and href:
            log(f"  {name} | {date}")
            fights = scrape_event_card(href)
            log(f"    {len(fights)} peleas")

            events.append({
                "name": name,
                "date": date,
                "url": href,
                "location": location,
                "fights": fights,
            })
            time.sleep(1)

    # Guardar
    UPCOMING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(UPCOMING_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    total = sum(len(e.get("fights", [])) for e in events)
    log(f"   {len(events)} eventos, {total} peleas → {UPCOMING_FILE}")
    return events


def scrape_event_card(event_url):
    """Scrapea la cartelera de un evento (solo nombres + weight class)."""
    r = requests.get(event_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    fights = []
    rows = soup.find_all("tr", class_="b-fight-details__table-row")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        fighters_col = cols[1]
        fighter_links = fighters_col.find_all("a")

        if len(fighter_links) >= 2:
            fa = clean(fighter_links[0].text)
            fb = clean(fighter_links[1].text)
        else:
            fps = fighters_col.find_all("p")
            if len(fps) >= 2:
                fa = clean(fps[0].text)
                fb = clean(fps[1].text)
            else:
                continue

        if not fa or not fb:
            continue

        wc = None
        if len(cols) > 6:
            wc = clean(cols[6].text)
        if not wc:
            for col in cols:
                txt = clean(col.text)
                if "weight" in txt.lower() or "bout" in txt.lower():
                    wc = txt
                    break

        fights.append({
            "fighter_a": fa,
            "fighter_b": fb,
            "weight_class": wc,
        })

    return fights


# ============================================================
# PARTE 2: POST-EVENT (resultados + stats + perfiles)
# ============================================================
def find_new_completed_events():
    """Busca eventos completados que no están en la BD."""
    log("🔍 Buscando eventos nuevos completados...")

    if not DB_PATH.exists():
        log("   No existe la BD. Ejecuta run_phase1.py primero.")
        return []

    url = "http://www.ufcstats.com/statistics/events/completed"
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    completed = []
    table = soup.find("table", class_="b-statistics__table-events")
    if not table:
        return []

    tbody = table.find("tbody")
    if not tbody:
        return []

    rows = tbody.find_all("tr", class_="b-statistics__table-row")

    for row in rows[:10]:
        link = row.find("a", class_="b-link")
        if not link:
            continue

        name = clean(link.text)
        href = link.get("href", "").strip()
        date_span = row.find("span", class_="b-statistics__date")
        date_str = clean(date_span.text) if date_span else None
        tds = row.find_all("td")
        location = clean(tds[-1].text) if len(tds) > 1 else None

        if name and href:
            completed.append({
                "name": name, "date": date_str,
                "url": href, "location": location,
            })

    conn = get_db()
    new_events = []
    try:
        for event in completed:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM events WHERE name = ?", (event["name"],)
            )
            if cursor.fetchone()[0] == 0:
                new_events.append(event)
                log(f"  🆕 {event['name']} ({event['date']})")
    finally:
        conn.close()

    if not new_events:
        log("   No hay eventos nuevos — la BD está al día")

    return new_events


def scrape_event_results(event_url):
    """Scrapea resultados completos de un evento."""
    r = requests.get(event_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    fights = []
    rows = soup.find_all("tr", class_="b-fight-details__table-row")

    for row in rows:
        fight_detail_url = row.get("data-link", "").strip()
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        result_col = cols[0]
        result_ps = result_col.find_all("p")

        fighters_col = cols[1]
        fighter_links = fighters_col.find_all("a")
        fighter_urls = []

        if len(fighter_links) >= 2:
            fa = clean(fighter_links[0].text)
            fb = clean(fighter_links[1].text)
            fighter_urls = [
                fighter_links[0].get("href", "").strip(),
                fighter_links[1].get("href", "").strip(),
            ]
        else:
            continue

        if not fa or not fb:
            continue

        winner = None
        is_draw = False
        is_nc = False
        if len(result_ps) >= 2:
            r_a = clean(result_ps[0].text).lower()
            r_b = clean(result_ps[1].text).lower()
            if r_a == "w":
                winner = fa
            elif r_b == "w":
                winner = fb
            elif r_a == "d":
                is_draw = True
            elif r_a == "nc":
                is_nc = True
        elif len(result_ps) == 1:
            r_text = clean(result_ps[0].text).lower()
            if r_text == "win" or r_text == "w":
                winner = fa
            elif r_text in ("draw", "d"):
                is_draw = True
            elif r_text in ("nc", "no contest"):
                is_nc = True

        wc = clean(cols[6].text) if len(cols) > 6 else None

        method_raw = None
        method_detail = None
        if len(cols) > 7:
            method_ps = cols[7].find_all("p")
            if method_ps:
                method_raw = clean(method_ps[0].text)
                if len(method_ps) > 1:
                    method_detail = clean(method_ps[1].text)

        method_norm = "other"
        if method_raw:
            ml = method_raw.lower()
            if "ko" in ml or "tko" in ml:
                method_norm = "ko"
            elif "sub" in ml:
                method_norm = "sub"
            elif "dec" in ml:
                method_norm = "dec"

        fight_round = None
        if len(cols) > 8:
            try:
                fight_round = int(clean(cols[8].text))
            except (ValueError, TypeError):
                pass

        fight_time = None
        fight_time_seconds = None
        if len(cols) > 9:
            fight_time = clean(cols[9].text)
            fight_time_seconds = parse_time_to_seconds(fight_time)

        fights.append({
            "fighter_a": fa, "fighter_b": fb,
            "fighter_a_url": fighter_urls[0] if len(fighter_urls) > 0 else None,
            "fighter_b_url": fighter_urls[1] if len(fighter_urls) > 1 else None,
            "winner": winner, "is_draw": is_draw, "is_no_contest": is_nc,
            "weight_class": wc, "method": method_norm,
            "method_raw": method_raw, "method_detail": method_detail,
            "round": fight_round, "time": fight_time,
            "time_seconds": fight_time_seconds, "detail_url": fight_detail_url,
        })

    return fights


def scrape_fight_stats_page(fight_url):
    """Scrapea stats round-by-round de una pelea individual."""
    if not fight_url:
        return {"totals": [], "sig_strikes": []}

    r = requests.get(fight_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")
    result = {"totals": [], "sig_strikes": []}

    tables = soup.find_all("table")
    totals_table = None
    sig_table = None

    for table in tables:
        thead = table.find("thead")
        if not thead:
            continue
        headers = [clean(th.text).lower() for th in thead.find_all("th")]
        header_str = " ".join(headers)
        if "ctrl" in header_str and totals_table is None:
            totals_table = table
        elif "head" in header_str and "body" in header_str and sig_table is None:
            sig_table = table

    def get_pair(col):
        ps = col.find_all("p")
        if len(ps) >= 2:
            return (clean(ps[0].text), clean(ps[1].text))
        return (clean(col.text), None)

    if totals_table:
        tbody = totals_table.find("tbody")
        if tbody:
            for ri, row in enumerate(tbody.find_all("tr")):
                cols = row.find_all("td")
                if len(cols) < 10:
                    continue
                p = [get_pair(c) for c in cols]
                sig_la, sig_aa = parse_stat_fraction(p[2][0])
                sig_lb, sig_ab = parse_stat_fraction(p[2][1])
                tot_la, tot_aa = parse_stat_fraction(p[4][0])
                tot_lb, tot_ab = parse_stat_fraction(p[4][1])
                td_la, td_aa = parse_stat_fraction(p[5][0])
                td_lb, td_ab = parse_stat_fraction(p[5][1])
                result["totals"].append({
                    "round": ri + 1,
                    "fighter_a": p[0][0], "fighter_b": p[0][1],
                    "fighter_a_stats": {
                        "knockdowns": safe_int(p[1][0]),
                        "sig_strikes_landed": sig_la, "sig_strikes_attempted": sig_aa,
                        "sig_strike_pct": p[3][0],
                        "total_strikes_landed": tot_la, "total_strikes_attempted": tot_aa,
                        "takedowns_landed": td_la, "takedowns_attempted": td_aa,
                        "takedown_pct": p[6][0],
                        "submission_attempts": safe_int(p[7][0]),
                        "reversals": safe_int(p[8][0]),
                        "control_time_seconds": parse_time_to_seconds(p[9][0]),
                    },
                    "fighter_b_stats": {
                        "knockdowns": safe_int(p[1][1]),
                        "sig_strikes_landed": sig_lb, "sig_strikes_attempted": sig_ab,
                        "sig_strike_pct": p[3][1],
                        "total_strikes_landed": tot_lb, "total_strikes_attempted": tot_ab,
                        "takedowns_landed": td_lb, "takedowns_attempted": td_ab,
                        "takedown_pct": p[6][1],
                        "submission_attempts": safe_int(p[7][1]),
                        "reversals": safe_int(p[8][1]),
                        "control_time_seconds": parse_time_to_seconds(p[9][1]),
                    },
                })

    if sig_table:
        tbody = sig_table.find("tbody")
        if tbody:
            for ri, row in enumerate(tbody.find_all("tr")):
                cols = row.find_all("td")
                if len(cols) < 9:
                    continue
                p = [get_pair(c) for c in cols]
                def ez(idx):
                    la, aa = parse_stat_fraction(p[idx][0])
                    lb, ab = parse_stat_fraction(p[idx][1])
                    return la, aa, lb, ab
                h_la, h_aa, h_lb, h_ab = ez(3)
                bo_la, bo_aa, bo_lb, bo_ab = ez(4)
                le_la, le_aa, le_lb, le_ab = ez(5)
                d_la, d_aa, d_lb, d_ab = ez(6)
                c_la, c_aa, c_lb, c_ab = ez(7)
                g_la, g_aa, g_lb, g_ab = ez(8)
                result["sig_strikes"].append({
                    "round": ri + 1,
                    "fighter_a": p[0][0], "fighter_b": p[0][1],
                    "fighter_a_strikes": {
                        "head_landed": h_la, "head_attempted": h_aa,
                        "body_landed": bo_la, "body_attempted": bo_aa,
                        "leg_landed": le_la, "leg_attempted": le_aa,
                        "distance_landed": d_la, "distance_attempted": d_aa,
                        "clinch_landed": c_la, "clinch_attempted": c_aa,
                        "ground_landed": g_la, "ground_attempted": g_aa,
                    },
                    "fighter_b_strikes": {
                        "head_landed": h_lb, "head_attempted": h_ab,
                        "body_landed": bo_lb, "body_attempted": bo_ab,
                        "leg_landed": le_lb, "leg_attempted": le_ab,
                        "distance_landed": d_lb, "distance_attempted": d_ab,
                        "clinch_landed": c_lb, "clinch_attempted": c_ab,
                        "ground_landed": g_lb, "ground_attempted": g_ab,
                    },
                })

    return result


def scrape_fighter_profile(profile_url):
    """Scrapea el perfil actualizado de un peleador."""
    r = requests.get(profile_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")
    details = {}

    record_el = soup.find("span", class_="b-content__title-record")
    if record_el:
        match = re.search(r"(\d+)-(\d+)-(\d+)", clean(record_el.text))
        if match:
            details["wins"] = int(match.group(1))
            details["losses"] = int(match.group(2))
            details["draws"] = int(match.group(3))

    career_stats_box = soup.find_all("div", class_="b-list__info-box")
    for box in career_stats_box:
        items = box.find_all("li", class_="b-list__box-list-item")
        for item in items:
            text = clean(item.text)
            stat_map = {
                "SLpM:": "slpm", "Str. Acc.:": "str_acc",
                "SApM:": "sapm", "Str. Def:": "str_def",
                "TD Avg.:": "td_avg", "TD Acc.:": "td_acc",
                "TD Def.:": "td_def", "Sub. Avg.:": "sub_avg",
            }
            for key, field in stat_map.items():
                if key in text:
                    val = text.split(":")[-1].strip()
                    if val and val != "--":
                        try:
                            details[field] = float(val.replace("%", "")) / 100 if "%" in val else float(val)
                        except ValueError:
                            details[field] = None

    return details


def process_new_event(event):
    """Procesa un evento nuevo: resultados + stats round-by-round + perfiles."""
    log(f"\n Procesando: {event['name']}")

    fights = scrape_event_results(event["url"])
    log(f"  {len(fights)} peleas con resultados")
    if not fights:
        return

    conn = get_db()
    try:
        event_id = generate_id(event["name"], event["url"])
        date_parsed = parse_date_ufcstats(event["date"])

        conn.execute("""
            INSERT OR IGNORE INTO events (event_id, name, date, date_parsed, location, org_id, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_id, event["name"], event["date"], date_parsed,
              event.get("location"), "ufc", event["url"]))

        fighters_to_update = set()

        for fight in fights:
            time.sleep(1.5)
            fa, fb = fight["fighter_a"], fight["fighter_b"]
            fight_id = generate_id(fa, fb, event_id)

            fa_row = conn.execute(
                "SELECT fighter_id, profile_url FROM fighters WHERE LOWER(name) = ?",
                (normalize_name(fa),)
            ).fetchone()
            fb_row = conn.execute(
                "SELECT fighter_id, profile_url FROM fighters WHERE LOWER(name) = ?",
                (normalize_name(fb),)
            ).fetchone()

            fa_id = fa_row["fighter_id"] if fa_row else None
            fb_id = fb_row["fighter_id"] if fb_row else None

            winner_id = None
            if fight["winner"] == fa and fa_id:
                winner_id = fa_id
            elif fight["winner"] == fb and fb_id:
                winner_id = fb_id

            conn.execute("""
                INSERT OR IGNORE INTO fights (
                    fight_id, event_id, fighter_a_id, fighter_b_id,
                    fighter_a_name, fighter_b_name,
                    winner_id, winner_name, is_draw, is_no_contest,
                    method, method_detail, round, time, time_seconds,
                    weight_class, fight_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fight_id, event_id, fa_id, fb_id, fa, fb,
                winner_id, fight.get("winner"),
                1 if fight["is_draw"] else 0, 1 if fight["is_no_contest"] else 0,
                fight["method"], fight.get("method_detail"),
                fight.get("round"), fight.get("time"), fight.get("time_seconds"),
                fight.get("weight_class"), fight.get("detail_url"),
            ))

            # Scrapear fight stats round-by-round
            if fight.get("detail_url"):
                log(f"    📊 Stats: {fa} vs {fb}")
                stats = scrape_fight_stats_page(fight["detail_url"])

                for rd in stats.get("totals", []):
                    rn = rd["round"]
                    sig_a, sig_b = {}, {}
                    for sig in stats.get("sig_strikes", []):
                        if sig["round"] == rn:
                            sig_a = sig.get("fighter_a_strikes", {})
                            sig_b = sig.get("fighter_b_strikes", {})
                            break

                    for side, fid, fname, st, sg in [
                        ("a", fa_id, fa, rd.get("fighter_a_stats", {}), sig_a),
                        ("b", fb_id, fb, rd.get("fighter_b_stats", {}), sig_b),
                    ]:
                        conn.execute("""
                            INSERT INTO fight_stats (
                                fight_id, fighter_id, fighter_name, round,
                                knockdowns, sig_strikes_landed, sig_strikes_attempted, sig_strike_pct,
                                total_strikes_landed, total_strikes_attempted,
                                takedowns_landed, takedowns_attempted, takedown_pct,
                                submission_attempts, reversals, control_time_seconds,
                                head_landed, head_attempted, body_landed, body_attempted,
                                leg_landed, leg_attempted,
                                distance_landed, distance_attempted,
                                clinch_landed, clinch_attempted,
                                ground_landed, ground_attempted
                            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            fight_id, fid, fname, rn,
                            st.get("knockdowns"), st.get("sig_strikes_landed"),
                            st.get("sig_strikes_attempted"), st.get("sig_strike_pct"),
                            st.get("total_strikes_landed"), st.get("total_strikes_attempted"),
                            st.get("takedowns_landed"), st.get("takedowns_attempted"),
                            st.get("takedown_pct"), st.get("submission_attempts"),
                            st.get("reversals"), st.get("control_time_seconds"),
                            sg.get("head_landed"), sg.get("head_attempted"),
                            sg.get("body_landed"), sg.get("body_attempted"),
                            sg.get("leg_landed"), sg.get("leg_attempted"),
                            sg.get("distance_landed"), sg.get("distance_attempted"),
                            sg.get("clinch_landed"), sg.get("clinch_attempted"),
                            sg.get("ground_landed"), sg.get("ground_attempted"),
                        ))

                ht = len(stats.get("totals", [])) > 0
                hs = len(stats.get("sig_strikes", [])) > 0
                dl = "full" if ht and hs else "basic" if ht else "result_only"
                conn.execute("""
                    INSERT OR REPLACE INTO data_quality (fight_id, detail_level, has_round_stats, has_sig_strikes, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (fight_id, dl, 1 if ht else 0, 1 if hs else 0, "ufcstats"))

            if fa_row and fa_row["profile_url"]:
                fighters_to_update.add((fa_id, fa, fa_row["profile_url"]))
            if fb_row and fb_row["profile_url"]:
                fighters_to_update.add((fb_id, fb, fb_row["profile_url"]))

        conn.commit()
        log(f"   {len(fights)} peleas insertadas con stats")

        # Actualizar perfiles de peleadores
        log(f"\n   Actualizando {len(fighters_to_update)} perfiles...")
        for fighter_id, fighter_name, profile_url in fighters_to_update:
            time.sleep(1)
            try:
                details = scrape_fighter_profile(profile_url)
                if details:
                    conn.execute("""
                        UPDATE fighters SET
                            wins = COALESCE(?, wins), losses = COALESCE(?, losses),
                            draws = COALESCE(?, draws), slpm = COALESCE(?, slpm),
                            str_acc = COALESCE(?, str_acc), sapm = COALESCE(?, sapm),
                            str_def = COALESCE(?, str_def), td_avg = COALESCE(?, td_avg),
                            td_acc = COALESCE(?, td_acc), td_def = COALESCE(?, td_def),
                            sub_avg = COALESCE(?, sub_avg), updated_at = CURRENT_TIMESTAMP
                        WHERE fighter_id = ?
                    """, (
                        details.get("wins"), details.get("losses"), details.get("draws"),
                        details.get("slpm"), details.get("str_acc"),
                        details.get("sapm"), details.get("str_def"),
                        details.get("td_avg"), details.get("td_acc"),
                        details.get("td_def"), details.get("sub_avg"),
                        fighter_id,
                    ))
                    log(f"     {fighter_name}")
            except Exception as e:
                log(f"     Error en {fighter_name}: {e}")

        conn.commit()
        log(f"   Perfiles actualizados")

    finally:
        conn.close()


# ============================================================
# GIT COMMIT + PUSH
# ============================================================
def git_commit_and_push():
    log(" Verificando cambios...")
    try:
        result = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True, timeout=30)
        if not result.stdout.strip():
            log("  No hay cambios")
            return False

        subprocess.run(["git", "add", "-A"], check=True, timeout=30)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "commit", "-m", f" Auto-update: {date_str}"],
                        check=True, timeout=30)
        subprocess.run(["git", "push"], check=True, timeout=60)
        log("   Push exitoso")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log(f"   Error git: {e}")
        return False


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="CageMind — Actualización de datos")
    parser.add_argument("--upcoming", action="store_true", help="Scrapear carteleras futuras")
    parser.add_argument("--post-event", action="store_true", help="Resultados + stats + perfiles")
    parser.add_argument("--all", action="store_true", help="Ejecutar todo")
    args = parser.parse_args()

    if not args.upcoming and not args.post_event and not args.all:
        args.all = True

    print("=" * 60)
    print("CAGEMIND — ACTUALIZACIÓN AUTOMÁTICA")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: {'upcoming' if args.upcoming else 'post-event' if args.post_event else 'all'}")
    print("=" * 60)

    start = time.time()
    changes = False

    if args.upcoming or args.all:
        print()
        if update_upcoming():
            changes = True

    if args.post_event or args.all:
        print()
        for event in find_new_completed_events():
            process_new_event(event)
            changes = True
            time.sleep(2)

    print()
    if changes:
        git_commit_and_push()
    else:
        log(" Sin cambios")

    print(f"\n{'='*60}\n Completado en {time.time()-start:.1f}s\n{'='*60}")


if __name__ == "__main__":
    main()
