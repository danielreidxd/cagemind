"""
CageMind — Actualización Incremental de Datos

Script diseñado para correr automáticamente via GitHub Actions cada 2 días.
Hace dos cosas:
  1. Scrapea eventos upcoming (carteleras futuras) desde UFCStats.com
  2. Detecta si hay un evento reciente cuyos resultados no están en la BD,
     y si lo hay, scrapea sus peleas, stats y actualiza la BD.

Uso:
    python update_data.py

Notas:
    - Este script NO re-scrapea todo. Solo agrega datos nuevos.
    - Si no hay eventos nuevos, no modifica nada.
    - Al final hace commit + push si hay cambios (cuando corre en GitHub Actions).
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURACIÓN
# ============================================================
DB_PATH = Path("db/ufc_database.db")
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


# ============================================================
# PARTE 1: SCRAPEAR UPCOMING EVENTS
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
        return events
    
    tbody = table.find("tbody")
    if not tbody:
        return events
    
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
            # Scrapear peleas de este evento
            log(f"  {name} | {date}")
            fights = scrape_event_fights(href)
            log(f"    {len(fights)} peleas")
            
            events.append({
                "name": name,
                "date": date,
                "url": href,
                "location": location,
                "fights": fights,
            })
            time.sleep(1)  # Rate limiting
    
    # Guardar
    UPCOMING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(UPCOMING_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    
    total_fights = sum(len(e.get("fights", [])) for e in events)
    log(f"  ✅ {len(events)} eventos, {total_fights} peleas → {UPCOMING_FILE}")
    
    return events


def scrape_event_fights(event_url):
    """Scrapea las peleas de un evento."""
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
            "weight_class": wc if wc else None,
        })
    
    return fights


# ============================================================
# PARTE 2: DETECTAR Y SCRAPEAR EVENTOS RECIENTES
# ============================================================
def get_latest_event_in_db():
    """Obtiene la fecha del evento más reciente en la base de datos."""
    if not DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute("SELECT MAX(date) FROM events")
        result = cursor.fetchone()
        return result[0] if result and result[0] else None
    finally:
        conn.close()


def get_completed_events_from_ufcstats():
    """Obtiene la lista de eventos completados desde UFCStats."""
    url = "http://www.ufcstats.com/statistics/events/completed"
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")
    
    events = []
    table = soup.find("table", class_="b-statistics__table-events")
    if not table:
        return events
    
    tbody = table.find("tbody")
    if not tbody:
        return events
    
    rows = tbody.find_all("tr", class_="b-statistics__table-row")
    
    for row in rows[:10]:  # Solo revisar los 10 más recientes
        link = row.find("a", class_="b-link")
        if not link:
            continue
        
        name = clean(link.text)
        href = link.get("href", "").strip()
        date_span = row.find("span", class_="b-statistics__date")
        date_str = clean(date_span.text) if date_span else None
        
        tds = row.find_all("td")
        location = clean(tds[-1].text) if len(tds) > 1 else None
        
        if name and href and date_str:
            events.append({
                "name": name,
                "date": date_str,
                "url": href,
                "location": location,
            })
    
    return events


def check_for_new_events():
    """Revisa si hay eventos completados que no están en la BD."""
    log("🔍 Buscando eventos nuevos completados...")
    
    latest_in_db = get_latest_event_in_db()
    log(f"  Último evento en BD: {latest_in_db}")
    
    completed = get_completed_events_from_ufcstats()
    log(f"  Eventos recientes en UFCStats: {len(completed)}")
    
    if not completed:
        log("  No se encontraron eventos completados")
        return []
    
    # Encontrar eventos que no están en la BD
    new_events = []
    
    if not DB_PATH.exists():
        log("  ⚠️ No existe la base de datos. Necesitas correr run_phase1.py primero.")
        return []
    
    conn = sqlite3.connect(DB_PATH)
    try:
        for event in completed:
            # Verificar si el evento ya existe por nombre
            cursor = conn.execute(
                "SELECT COUNT(*) FROM events WHERE name = ?",
                (event["name"],)
            )
            count = cursor.fetchone()[0]
            if count == 0:
                new_events.append(event)
                log(f"  🆕 Evento nuevo: {event['name']} ({event['date']})")
    finally:
        conn.close()
    
    if not new_events:
        log("  ✅ No hay eventos nuevos — la BD está al día")
    
    return new_events


def scrape_new_event_details(event):
    """Scrapea los detalles completos de un evento nuevo."""
    log(f"  📥 Scrapeando detalles de: {event['name']}")
    
    r = requests.get(event["url"], headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")
    
    fights = []
    rows = soup.find_all("tr", class_="b-fight-details__table-row")
    
    for row in rows:
        # Obtener URL de detalle de la pelea
        fight_url = row.get("data-link", "").strip()
        
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        
        # Resultado (W/L)
        result_col = cols[0]
        result_ps = result_col.find_all("p")
        
        # Peleadores
        fighters_col = cols[1]
        fighter_links = fighters_col.find_all("a")
        
        if len(fighter_links) >= 2:
            fa = clean(fighter_links[0].text)
            fb = clean(fighter_links[1].text)
        else:
            continue
        
        if not fa or not fb:
            continue
        
        # Determinar ganador
        winner = None
        if len(result_ps) >= 2:
            r_a = clean(result_ps[0].text).lower()
            r_b = clean(result_ps[1].text).lower()
            if r_a == "w":
                winner = fa
            elif r_b == "w":
                winner = fb
        
        # Weight class
        wc = None
        if len(cols) > 6:
            wc = clean(cols[6].text)
        
        # Método
        method = None
        if len(cols) > 7:
            method_ps = cols[7].find_all("p")
            if method_ps:
                method = clean(method_ps[0].text)
        
        # Round
        fight_round = None
        if len(cols) > 8:
            round_text = clean(cols[8].text)
            try:
                fight_round = int(round_text)
            except (ValueError, TypeError):
                pass
        
        # Time
        fight_time = None
        if len(cols) > 9:
            fight_time = clean(cols[9].text)
        
        fights.append({
            "fighter_a": fa,
            "fighter_b": fb,
            "winner": winner,
            "weight_class": wc,
            "method": method,
            "round": fight_round,
            "time": fight_time,
            "detail_url": fight_url,
        })
        
    log(f"    {len(fights)} peleas encontradas")
    return fights


def insert_new_event(event, fights):
    """Inserta un evento nuevo y sus peleas en la BD."""
    if not fights:
        log(f"  ⚠️ Sin peleas para {event['name']}, saltando")
        return
    
    log(f"  💾 Insertando {event['name']} en la BD...")
    
    conn = sqlite3.connect(DB_PATH)
    try:
        # Insertar evento
        conn.execute("""
            INSERT OR IGNORE INTO events (name, date, location, organization)
            VALUES (?, ?, ?, ?)
        """, (event["name"], event["date"], event.get("location"), "UFC"))
        
        # Obtener event_id
        cursor = conn.execute("SELECT id FROM events WHERE name = ?", (event["name"],))
        row = cursor.fetchone()
        if not row:
            log(f"    ⚠️ No se pudo obtener ID del evento")
            return
        event_id = row[0]
        
        # Insertar peleas
        inserted = 0
        for fight in fights:
            # Buscar fighter IDs
            fa_id = get_fighter_id(conn, fight["fighter_a"])
            fb_id = get_fighter_id(conn, fight["fighter_b"])
            
            # Determinar método normalizado
            method_raw = (fight.get("method") or "").lower()
            if "ko" in method_raw or "tko" in method_raw:
                method_norm = "ko"
            elif "sub" in method_raw:
                method_norm = "sub"
            elif "dec" in method_raw:
                method_norm = "dec"
            else:
                method_norm = "other"
            
            # Determinar ganador como fighter_a o fighter_b
            winner_val = None
            if fight.get("winner"):
                if fight["winner"] == fight["fighter_a"]:
                    winner_val = "a"
                elif fight["winner"] == fight["fighter_b"]:
                    winner_val = "b"
            
            conn.execute("""
                INSERT OR IGNORE INTO fights 
                (event_id, date, fighter_a, fighter_b, fighter_a_id, fighter_b_id,
                 winner, method, method_detail, round, time, weight_class)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, event["date"], fight["fighter_a"], fight["fighter_b"],
                fa_id, fb_id, winner_val, method_norm, fight.get("method"),
                fight.get("round"), fight.get("time"), fight.get("weight_class"),
            ))
            inserted += 1
        
        conn.commit()
        log(f"    ✅ {inserted} peleas insertadas")
        
    finally:
        conn.close()


def get_fighter_id(conn, name):
    """Busca el ID de un peleador por nombre."""
    cursor = conn.execute(
        "SELECT id FROM fighters WHERE name = ? COLLATE NOCASE",
        (name,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


# ============================================================
# PARTE 3: GIT COMMIT + PUSH (solo en GitHub Actions)
# ============================================================
def git_commit_and_push():
    """Hace commit y push si hay cambios."""
    log("📤 Verificando cambios para commit...")
    
    try:
        # Verificar si hay cambios
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=30
        )
        
        if not result.stdout.strip():
            log("  No hay cambios para commitear")
            return False
        
        log("  Cambios detectados:")
        for line in result.stdout.strip().split("\n"):
            log(f"    {line}")
        
        # Git add
        subprocess.run(["git", "add", "-A"], check=True, timeout=30)
        
        # Git commit
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"🤖 Auto-update: datos actualizados {date_str}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True, timeout=30
        )
        
        # Git push
        subprocess.run(["git", "push"], check=True, timeout=60)
        
        log("  ✅ Commit y push exitoso")
        return True
        
    except subprocess.CalledProcessError as e:
        log(f"  ⚠️ Error en git: {e}")
        return False
    except FileNotFoundError:
        log("  ⚠️ Git no disponible (probablemente corriendo en local)")
        return False


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("CAGEMIND — ACTUALIZACIÓN AUTOMÁTICA")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    start = time.time()
    changes_made = False
    
    # 1. Actualizar upcoming events
    print()
    events = update_upcoming()
    if events:
        changes_made = True
    
    # 2. Buscar y scrapear eventos nuevos completados
    print()
    new_events = check_for_new_events()
    
    for event in new_events:
        fights = scrape_new_event_details(event)
        insert_new_event(event, fights)
        changes_made = True
        time.sleep(2)  # Rate limiting entre eventos
    
    # 3. Git commit + push (si estamos en GitHub Actions)
    print()
    if changes_made:
        git_commit_and_push()
    else:
        log("📭 Sin cambios — nada que commitear")
    
    elapsed = time.time() - start
    print()
    print("=" * 60)
    print(f"✅ Actualización completada en {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()