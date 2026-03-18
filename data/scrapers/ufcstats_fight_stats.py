"""
Scraper de estadísticas detalladas por pelea desde UFCStats.com.

Para cada pelea, obtiene stats round-by-round:
- Knockdowns (KD)
- Significant Strikes (landed / attempted)
- Significant Strikes por zona (head, body, leg)
- Significant Strikes por posición (distance, clinch, ground)
- Total Strikes
- Takedowns (landed / attempted)
- Submission Attempts
- Reversals
- Control Time

Uso:
    python -m data.scrapers.ufcstats_fight_stats
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tqdm import tqdm

from config.settings import RAW_UFCSTATS_DIR, setup_logging
from data.scrapers.utils import (
    ScraperClient,
    CheckpointManager,
    clean_text,
    parse_stat_fraction,
    parse_time,
)

logger = setup_logging("ufcstats_fight_stats")

OUTPUT_FILE = RAW_UFCSTATS_DIR / "all_fight_stats.json"
FIGHTS_FILE = RAW_UFCSTATS_DIR / "all_fights.json"


def _extract_paired_values(cols, col_index: int) -> tuple:
    """
    Extrae un par de valores apilados (fighter_a y fighter_b) de una columna.
    UFCStats apila los valores de ambos peleadores en paragraphs <p> dentro de cada <td>.
    """
    if col_index >= len(cols):
        return (None, None)

    cell = cols[col_index]
    paragraphs = cell.find_all("p")

    if len(paragraphs) >= 2:
        val_a = clean_text(paragraphs[0].text)
        val_b = clean_text(paragraphs[1].text)
        return (val_a, val_b)

    # Fallback: intentar separar por saltos de línea
    text = clean_text(cell.text)
    parts = [p.strip() for p in text.split() if p.strip()]
    if len(parts) >= 2:
        return (parts[0], parts[1])

    return (text, None)


def _safe_int(v):
    """Convierte a int de forma segura."""
    try:
        return int(v) if v and v != "--" else None
    except (ValueError, TypeError):
        return None


def _parse_table_rows(table) -> list[dict]:
    """
    Parsea las filas de una tabla de UFCStats.
    Cada fila tiene pares de valores (fighter_a / fighter_b) en <p> tags.
    Retorna lista de dicts con los valores extraídos por columna.
    """
    tbody = table.find("tbody")
    if not tbody:
        return []

    rows_data = []
    rows = tbody.find_all("tr")
    for row in rows:
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


def scrape_fight_details(client: ScraperClient, fight_url: str) -> dict:
    """
    Scrapea las estadísticas detalladas de una pelea individual.
    
    Estructura real de la página (4 tablas):
    - Tabla 0: Totals resumen (sin clase CSS) — Fighter, KD, Sig.str., Sig.str.%, Total str., Td, Td%, Sub.att, Rev., Ctrl
    - Tabla 1: Totals por round (clase js-fight-table) — mismo formato
    - Tabla 2: Sig Strikes resumen (sin clase CSS) — Fighter, Sig.str, Sig.str.%, Head, Body, Leg, Distance, Clinch, Ground
    - Tabla 3: Sig Strikes por round (clase js-fight-table) — mismo formato
    """
    soup = client.get_soup(fight_url)
    result = {
        "fight_url": fight_url,
        "totals": [],
        "sig_strikes": [],
        "method_detail": None,
    }

    # Extraer detalle del método de victoria
    method_items = soup.find_all("i", class_="b-fight-details__text-item")
    for item in method_items:
        text = clean_text(item.text)
        if "Details:" in text:
            result["method_detail"] = text.replace("Details:", "").strip()

    # Buscar TODAS las tablas de la página
    tables = soup.find_all("table")

    # Clasificar tablas por sus headers
    totals_table = None
    sig_strikes_table = None

    for table in tables:
        thead = table.find("thead")
        if not thead:
            continue

        headers = [clean_text(th.text).lower() for th in thead.find_all("th")]
        header_str = " ".join(headers)

        # Tabla de Totals: tiene "ctrl" en headers
        if "ctrl" in header_str and totals_table is None:
            totals_table = table

        # Tabla de Sig Strikes: tiene "head" y "body" en headers
        elif "head" in header_str and "body" in header_str and sig_strikes_table is None:
            sig_strikes_table = table

    # ===============================================
    # Parsear TOTALS (tabla 0 — resumen)
    # ===============================================
    if totals_table:
        rows_data = _parse_table_rows(totals_table)
        for round_idx, row_vals in enumerate(rows_data):
            if len(row_vals) < 10:
                continue

            # Col 0: Fighter, 1: KD, 2: Sig.str., 3: Sig.str.%,
            # 4: Total str., 5: Td, 6: Td%, 7: Sub.att, 8: Rev., 9: Ctrl
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
                    "knockdowns": _safe_int(kd_a),
                    "sig_strikes_landed": sig_landed_a,
                    "sig_strikes_attempted": sig_att_a,
                    "sig_strike_pct": sig_pct_a,
                    "total_strikes_landed": total_landed_a,
                    "total_strikes_attempted": total_att_a,
                    "takedowns_landed": td_landed_a,
                    "takedowns_attempted": td_att_a,
                    "takedown_pct": td_pct_a,
                    "submission_attempts": _safe_int(sub_a),
                    "reversals": _safe_int(rev_a),
                    "control_time": ctrl_a,
                    "control_time_seconds": parse_time(ctrl_a),
                },
                "fighter_b_stats": {
                    "knockdowns": _safe_int(kd_b),
                    "sig_strikes_landed": sig_landed_b,
                    "sig_strikes_attempted": sig_att_b,
                    "sig_strike_pct": sig_pct_b,
                    "total_strikes_landed": total_landed_b,
                    "total_strikes_attempted": total_att_b,
                    "takedowns_landed": td_landed_b,
                    "takedowns_attempted": td_att_b,
                    "takedown_pct": td_pct_b,
                    "submission_attempts": _safe_int(sub_b),
                    "reversals": _safe_int(rev_b),
                    "control_time": ctrl_b,
                    "control_time_seconds": parse_time(ctrl_b),
                },
            }
            result["totals"].append(round_data)

    # ===============================================
    # Parsear SIG STRIKES (tabla 2 — resumen)
    # ===============================================
    if sig_strikes_table:
        rows_data = _parse_table_rows(sig_strikes_table)
        for round_idx, row_vals in enumerate(rows_data):
            if len(row_vals) < 9:
                continue

            # Col 0: Fighter, 1: Sig.str, 2: Sig.str.%,
            # 3: Head, 4: Body, 5: Leg, 6: Distance, 7: Clinch, 8: Ground
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
            result["sig_strikes"].append(sig_data)

    return result


def scrape_all_fight_stats():
    """
    Scrapea estadísticas detalladas de todas las peleas.
    Lee la lista de peleas de all_fights.json y visita cada URL de detalles.
    """
    checkpoint = CheckpointManager("ufcstats_fight_stats")

    # Cargar peleas
    if not FIGHTS_FILE.exists():
        logger.error(
            f"No se encontró {FIGHTS_FILE}. "
            "Ejecuta primero: python -m data.scrapers.ufcstats_events"
        )
        return

    with open(FIGHTS_FILE, "r") as f:
        all_fights = json.load(f)

    # Cargar stats previas
    all_stats = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r") as f:
            all_stats = json.load(f)

    existing_urls = {s["fight_url"] for s in all_stats}

    logger.info("=" * 60)
    logger.info("SCRAPING DE ESTADÍSTICAS DETALLADAS POR PELEA")
    logger.info("=" * 60)

    fights_pending = [
        f for f in all_fights
        if f.get("fight_details_url")
        and f["fight_details_url"] not in existing_urls
        and not checkpoint.is_completed(f["fight_id"])
    ]

    logger.info(f"Total peleas: {len(all_fights)}")
    logger.info(f"Peleas pendientes: {len(fights_pending)}")

    with ScraperClient() as client:
        for fight in tqdm(fights_pending, desc="Fight Stats"):
            url = fight["fight_details_url"]
            try:
                stats = scrape_fight_details(client, url)
                stats["fight_id"] = fight["fight_id"]
                stats["event_id"] = fight["event_id"]
                stats["fighter_a"] = fight["fighter_a"]
                stats["fighter_b"] = fight["fighter_b"]
                all_stats.append(stats)
                checkpoint.mark_completed(fight["fight_id"])

            except Exception as e:
                logger.error(
                    f"Error en pelea {fight['fighter_a']} vs {fight['fighter_b']}: {e}"
                )
                continue

            # Guardar progreso cada 100 peleas
            if checkpoint.completed_count % 100 == 0:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(all_stats, f, indent=2, ensure_ascii=False)
                logger.info(f"  Progreso guardado: {checkpoint.completed_count} peleas")

    # Guardar final
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_stats, f, indent=2, ensure_ascii=False)

    logger.info(f"Scraping de fight stats completado: {len(all_stats)} peleas con stats")

    return all_stats


if __name__ == "__main__":
    scrape_all_fight_stats()