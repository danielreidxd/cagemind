
from __future__ import annotations
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from config.settings import (
    RAW_UFCSTATS_DIR,
    PROCESSED_DIR,
    EXPORTS_DIR,
    setup_logging,
)
from db.schema import init_database, get_connection, get_table_counts
from data.scrapers.utils import generate_id

logger = setup_logging("pipeline")


# ============================================================
# HELPERS DE LIMPIEZA
# ============================================================

def parse_date_ufcstats(date_str: str) -> str | None:
    """
    Parsea fechas de UFCStats (formato: 'March 15, 2026') a 'YYYY-MM-DD'.
    """
    if not date_str or date_str.strip() == "--":
        return None
    
    date_str = date_str.strip()
    formats = [
        "%B %d, %Y",      # March 15, 2026
        "%b %d, %Y",      # Mar 15, 2026
        "%b. %d, %Y",     # Mar. 15, 2026
        "%Y-%m-%d",        # Ya parseada
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    logger.warning(f"No se pudo parsear fecha: '{date_str}'")
    return None


def normalize_fighter_name(name: str) -> str:
    """Normaliza el nombre de un peleador para matching."""
    if not name:
        return ""
    # Lowercase, remover acentos comunes, strip extra whitespace
    name = name.strip().lower()
    name = re.sub(r"\s+", " ", name)
    return name


def build_fighter_id_map(fighters_data: list[dict]) -> dict:
    """
    Construye un mapa nombre_normalizado -> fighter_id para
    poder linkear peleas con peleadores.
    """
    id_map = {}
    for fighter in fighters_data:
        name = fighter.get("name", "")
        norm_name = normalize_fighter_name(name)
        fighter_id = generate_id(name, fighter.get("profile_url", ""))
        id_map[norm_name] = fighter_id
        # También mapear por URL
        if fighter.get("profile_url"):
            id_map[fighter["profile_url"]] = fighter_id
    return id_map


# ============================================================
# CARGA A SQLITE
# ============================================================

def load_fighters(conn: sqlite3.Connection, fighters_data: list[dict]):
    """Carga peleadores a la base de datos."""
    logger.info(f"Cargando {len(fighters_data)} peleadores...")
    
    for fighter in tqdm(fighters_data, desc="Cargando fighters"):
        fighter_id = generate_id(
            fighter.get("name", ""),
            fighter.get("profile_url", "")
        )
        
        conn.execute("""
            INSERT OR REPLACE INTO fighters (
                fighter_id, name, first_name, last_name, nickname, dob,
                height_inches, weight_lbs, reach_inches, stance,
                wins, losses, draws,
                slpm, str_acc, sapm, str_def,
                td_avg, td_acc, td_def, sub_avg,
                has_belt, profile_url, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            fighter_id,
            fighter.get("name"),
            fighter.get("first_name"),
            fighter.get("last_name"),
            fighter.get("nickname"),
            fighter.get("dob"),
            fighter.get("height_inches"),
            fighter.get("weight_lbs"),
            fighter.get("reach_inches"),
            fighter.get("stance"),
            fighter.get("wins", 0),
            fighter.get("losses", 0),
            fighter.get("draws", 0),
            fighter.get("slpm"),
            fighter.get("str_acc"),
            fighter.get("sapm"),
            fighter.get("str_def"),
            fighter.get("td_avg"),
            fighter.get("td_acc"),
            fighter.get("td_def"),
            fighter.get("sub_avg"),
            1 if fighter.get("has_belt") else 0,
            fighter.get("profile_url"),
            "ufcstats",
        ))
    
    conn.commit()
    logger.info("Peleadores cargados exitosamente")


def load_events(conn: sqlite3.Connection, events_data: list[dict]):
    """Carga eventos a la base de datos."""
    logger.info(f"Cargando {len(events_data)} eventos...")
    
    for event in tqdm(events_data, desc="Cargando events"):
        date_parsed = parse_date_ufcstats(event.get("date"))
        
        conn.execute("""
            INSERT OR REPLACE INTO events (
                event_id, name, date, date_parsed, location, org_id, url
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event["event_id"],
            event["name"],
            event.get("date"),
            date_parsed,
            event.get("location"),
            "ufc",
            event.get("url"),
        ))
    
    conn.commit()
    logger.info("Eventos cargados exitosamente")


def load_fights(conn: sqlite3.Connection, fights_data: list[dict], fighter_id_map: dict):
    """Carga peleas a la base de datos, linkeando con fighter IDs."""
    logger.info(f"Cargando {len(fights_data)} peleas...")
    
    linked = 0
    for fight in tqdm(fights_data, desc="Cargando fights"):
        # Intentar resolver fighter IDs
        a_norm = normalize_fighter_name(fight.get("fighter_a", ""))
        b_norm = normalize_fighter_name(fight.get("fighter_b", ""))
        
        fighter_a_id = (
            fighter_id_map.get(fight.get("fighter_a_url"))
            or fighter_id_map.get(a_norm)
        )
        fighter_b_id = (
            fighter_id_map.get(fight.get("fighter_b_url"))
            or fighter_id_map.get(b_norm)
        )
        
        winner_name = fight.get("winner")
        winner_id = None
        if winner_name:
            w_norm = normalize_fighter_name(winner_name)
            winner_id = fighter_id_map.get(w_norm)
        
        if fighter_a_id and fighter_b_id:
            linked += 1
        
        conn.execute("""
            INSERT OR REPLACE INTO fights (
                fight_id, event_id, fighter_a_id, fighter_b_id,
                fighter_a_name, fighter_b_name,
                winner_id, winner_name,
                is_draw, is_no_contest,
                method, method_detail, round, time, time_seconds,
                weight_class, fight_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fight["fight_id"],
            fight["event_id"],
            fighter_a_id,
            fighter_b_id,
            fight["fighter_a"],
            fight["fighter_b"],
            winner_id,
            winner_name,
            1 if fight.get("is_draw") else 0,
            1 if fight.get("is_no_contest") else 0,
            fight.get("method"),
            fight.get("method_detail"),
            fight.get("round"),
            fight.get("time"),
            fight.get("time_seconds"),
            fight.get("weight_class"),
            fight.get("fight_details_url"),
        ))
    
    conn.commit()
    pct = (linked / len(fights_data) * 100) if fights_data else 0
    logger.info(f"Peleas cargadas. {linked}/{len(fights_data)} ({pct:.1f}%) linkeadas con fighter IDs")


def load_fight_stats(conn: sqlite3.Connection, stats_data: list[dict], fighter_id_map: dict):
    """Carga estadísticas round-by-round a la base de datos."""
    logger.info(f"Cargando stats de {len(stats_data)} peleas...")
    
    total_rows = 0
    for fight_stats in tqdm(stats_data, desc="Cargando fight_stats"):
        fight_id = fight_stats.get("fight_id")
        
        # Procesar totals (stats generales por round)
        for round_data in fight_stats.get("totals", []):
            round_num = round_data.get("round", 0)
            
            # Buscar sig strikes matching de la misma pelea/round
            sig_data_a = {}
            sig_data_b = {}
            for sig in fight_stats.get("sig_strikes", []):
                if sig.get("round") == round_num:
                    sig_data_a = sig.get("fighter_a_strikes", {})
                    sig_data_b = sig.get("fighter_b_strikes", {})
                    break
            
            # Fighter A
            a_stats = round_data.get("fighter_a_stats", {})
            a_name = round_data.get("fighter_a", "")
            a_id = fighter_id_map.get(normalize_fighter_name(a_name))
            
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fight_id, a_id, a_name, round_num,
                a_stats.get("knockdowns"),
                a_stats.get("sig_strikes_landed"),
                a_stats.get("sig_strikes_attempted"),
                a_stats.get("sig_strike_pct"),
                a_stats.get("total_strikes_landed"),
                a_stats.get("total_strikes_attempted"),
                a_stats.get("takedowns_landed"),
                a_stats.get("takedowns_attempted"),
                a_stats.get("takedown_pct"),
                a_stats.get("submission_attempts"),
                a_stats.get("reversals"),
                a_stats.get("control_time_seconds"),
                sig_data_a.get("head_landed"),
                sig_data_a.get("head_attempted"),
                sig_data_a.get("body_landed"),
                sig_data_a.get("body_attempted"),
                sig_data_a.get("leg_landed"),
                sig_data_a.get("leg_attempted"),
                sig_data_a.get("distance_landed"),
                sig_data_a.get("distance_attempted"),
                sig_data_a.get("clinch_landed"),
                sig_data_a.get("clinch_attempted"),
                sig_data_a.get("ground_landed"),
                sig_data_a.get("ground_attempted"),
            ))
            total_rows += 1
            
            # Fighter B
            b_stats = round_data.get("fighter_b_stats", {})
            b_name = round_data.get("fighter_b", "")
            b_id = fighter_id_map.get(normalize_fighter_name(b_name))
            
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fight_id, b_id, b_name, round_num,
                b_stats.get("knockdowns"),
                b_stats.get("sig_strikes_landed"),
                b_stats.get("sig_strikes_attempted"),
                b_stats.get("sig_strike_pct"),
                b_stats.get("total_strikes_landed"),
                b_stats.get("total_strikes_attempted"),
                b_stats.get("takedowns_landed"),
                b_stats.get("takedowns_attempted"),
                b_stats.get("takedown_pct"),
                b_stats.get("submission_attempts"),
                b_stats.get("reversals"),
                b_stats.get("control_time_seconds"),
                sig_data_b.get("head_landed"),
                sig_data_b.get("head_attempted"),
                sig_data_b.get("body_landed"),
                sig_data_b.get("body_attempted"),
                sig_data_b.get("leg_landed"),
                sig_data_b.get("leg_attempted"),
                sig_data_b.get("distance_landed"),
                sig_data_b.get("distance_attempted"),
                sig_data_b.get("clinch_landed"),
                sig_data_b.get("clinch_attempted"),
                sig_data_b.get("ground_landed"),
                sig_data_b.get("ground_attempted"),
            ))
            total_rows += 1
        
        # Registrar calidad de datos
        has_totals = len(fight_stats.get("totals", [])) > 0
        has_sig = len(fight_stats.get("sig_strikes", [])) > 0
        
        if has_totals and has_sig:
            detail_level = "full"
        elif has_totals:
            detail_level = "basic"
        else:
            detail_level = "result_only"
        
        conn.execute("""
            INSERT OR REPLACE INTO data_quality (
                fight_id, detail_level, has_round_stats, has_sig_strikes, source
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            fight_id, detail_level,
            1 if has_totals else 0,
            1 if has_sig else 0,
            "ufcstats",
        ))
    
    conn.commit()
    logger.info(f"Fight stats cargadas: {total_rows} filas de estadísticas")


# ============================================================
# EXPORTACIÓN A CSV
# ============================================================

def export_to_csv(conn: sqlite3.Connection):
    """Exporta todas las tablas a CSV como respaldo."""
    logger.info("Exportando a CSV...")
    
    tables = ["fighters", "events", "fights", "fight_stats", "data_quality"]
    
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        output_path = EXPORTS_DIR / f"{table}.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"  {table}.csv: {len(df)} filas")
    
    logger.info(f"CSVs exportados a: {EXPORTS_DIR}")


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def run_pipeline():
    """
    Ejecuta el pipeline completo:
    1. Lee datos crudos JSON
    2. Inicializa la base de datos
    3. Limpia y carga datos
    4. Exporta a CSV
    """
    logger.info("=" * 60)
    logger.info("PIPELINE DE LIMPIEZA Y CARGA DE DATOS")
    logger.info("=" * 60)
    
    # Verificar que existan los archivos de datos crudos
    fighters_file = RAW_UFCSTATS_DIR / "all_fighters.json"
    events_file = RAW_UFCSTATS_DIR / "all_events.json"
    fights_file = RAW_UFCSTATS_DIR / "all_fights.json"
    stats_file = RAW_UFCSTATS_DIR / "all_fight_stats.json"
    
    # Leer datos disponibles
    fighters_data = []
    events_data = []
    fights_data = []
    stats_data = []
    
    if fighters_file.exists():
        with open(fighters_file, "r") as f:
            fighters_data = json.load(f)
        logger.info(f"Peleadores crudos: {len(fighters_data)}")
    else:
        logger.warning(f"No se encontró {fighters_file}")
    
    if events_file.exists():
        with open(events_file, "r") as f:
            events_data = json.load(f)
        logger.info(f"Eventos crudos: {len(events_data)}")
    else:
        logger.warning(f"No se encontró {events_file}")
    
    if fights_file.exists():
        with open(fights_file, "r") as f:
            fights_data = json.load(f)
        logger.info(f"Peleas crudas: {len(fights_data)}")
    else:
        logger.warning(f"No se encontró {fights_file}")
    
    if stats_file.exists():
        with open(stats_file, "r") as f:
            stats_data = json.load(f)
        logger.info(f"Fight stats crudas: {len(stats_data)}")
    else:
        logger.warning(f"No se encontró {stats_file}")
    
    if not fighters_data and not events_data:
        logger.error("No hay datos crudos para procesar. Ejecuta los scrapers primero.")
        return
    
    # Inicializar BD
    conn = init_database()
    
    # Construir mapa de IDs
    fighter_id_map = build_fighter_id_map(fighters_data)
    
    # Cargar datos
    if fighters_data:
        load_fighters(conn, fighters_data)
    
    if events_data:
        load_events(conn, events_data)
    
    if fights_data:
        load_fights(conn, fights_data, fighter_id_map)
    
    if stats_data:
        load_fight_stats(conn, stats_data, fighter_id_map)
    
    # Exportar CSVs
    export_to_csv(conn)
    
    # Resumen final
    counts = get_table_counts(conn)
    logger.info("=" * 60)
    logger.info("RESUMEN DE BASE DE DATOS")
    logger.info("=" * 60)
    for table, count in counts.items():
        logger.info(f"  {table}: {count:,} filas")
    
    conn.close()
    logger.info("Pipeline completado exitosamente")


if __name__ == "__main__":
    run_pipeline()
