"""
CageMind — Cargar Round Stats a SQLite

Después de correr scrape_round_stats.py, ejecuta este script para:
1. Leer all_round_stats.json
2. Limpiar la tabla fight_stats existente (solo tiene totals)
3. Cargar las stats round-by-round con round numbers correctos
4. Verificar integridad

Uso:
    cd cagemind
    python load_round_stats.py

IMPORTANTE: Haz backup de tu BD antes de correr esto.
    copy db/ufc_predictor.db db/ufc_predictor_backup.db
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "db" / "ufc_predictor.db"
ROUND_STATS_FILE = PROJECT_ROOT / "data" / "raw" / "ufcstats" / "all_round_stats.json"
BACKUP_PATH = PROJECT_ROOT / "db" / "ufc_predictor_pre_rounds.db"


def normalize_fighter_name(name):
    if not name:
        return ""
    import re
    name = name.strip().lower()
    name = re.sub(r"\s+", " ", name)
    return name


def generate_id(*args):
    import hashlib
    raw = "|".join(str(a) for a in args)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def main():
    print("=" * 60)
    print("CAGEMIND — CARGAR ROUND STATS A SQLITE")
    print("=" * 60)

    # Verificar archivos
    if not ROUND_STATS_FILE.exists():
        print(f"ERROR: No se encontró {ROUND_STATS_FILE}")
        print("Ejecuta primero: python scrape_round_stats.py")
        return

    if not DB_PATH.exists():
        print(f"ERROR: No se encontró la base de datos {DB_PATH}")
        return

    # Cargar round stats
    with open(ROUND_STATS_FILE) as f:
        all_stats = json.load(f)
    print(f"Round stats cargadas: {len(all_stats)} peleas")

    # Validar que tenemos datos multi-round
    multi = sum(1 for s in all_stats if len(s.get("totals_by_round", [])) > 1)
    print(f"Peleas con múltiples rounds: {multi}")

    if multi == 0:
        print("ADVERTENCIA: No hay peleas con datos multi-round.")
        print("Verifica que scrape_round_stats.py terminó correctamente.")
        resp = input("¿Continuar de todas formas? (s/n): ")
        if resp.lower() != "s":
            return

    # Backup de la BD
    import shutil
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Backup creado: {BACKUP_PATH}")

    # Conectar a BD
    conn = sqlite3.connect(str(DB_PATH))

    # Construir mapa de fighter IDs
    fighters_df = pd.read_sql("SELECT fighter_id, name FROM fighters", conn)
    fighter_id_map = {}
    for _, row in fighters_df.iterrows():
        norm = normalize_fighter_name(row["name"])
        fighter_id_map[norm] = row["fighter_id"]
    print(f"Mapa de fighter IDs: {len(fighter_id_map)} peleadores")

    # Contar stats actuales
    old_count = pd.read_sql("SELECT COUNT(*) as cnt FROM fight_stats", conn).iloc[0, 0]
    print(f"\nStats actuales en BD: {old_count} filas (solo totals)")

    # Limpiar tabla fight_stats
    print("Limpiando tabla fight_stats...")
    conn.execute("DELETE FROM fight_stats")
    conn.commit()

    # Cargar round stats
    print("Cargando stats round-by-round...")
    total_rows = 0
    fights_loaded = 0
    fights_skipped = 0

    for fight_stats in tqdm(all_stats, desc="Cargando"):
        fight_id = fight_stats.get("fight_id")
        if not fight_id:
            fights_skipped += 1
            continue

        totals = fight_stats.get("totals_by_round", [])
        sig_strikes = fight_stats.get("sig_strikes_by_round", [])

        if not totals:
            fights_skipped += 1
            continue

        # Indexar sig strikes por round para merge
        sig_by_round = {}
        for ss in sig_strikes:
            sig_by_round[ss["round"]] = ss

        for round_data in totals:
            round_num = round_data["round"]
            sig_data = sig_by_round.get(round_num, {})

            # Fighter A
            a_name = round_data.get("fighter_a", "")
            a_id = fighter_id_map.get(normalize_fighter_name(a_name))
            a_stats = round_data.get("fighter_a_stats", {})
            a_sig = sig_data.get("fighter_a_strikes", {})

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
                a_sig.get("head_landed"),
                a_sig.get("head_attempted"),
                a_sig.get("body_landed"),
                a_sig.get("body_attempted"),
                a_sig.get("leg_landed"),
                a_sig.get("leg_attempted"),
                a_sig.get("distance_landed"),
                a_sig.get("distance_attempted"),
                a_sig.get("clinch_landed"),
                a_sig.get("clinch_attempted"),
                a_sig.get("ground_landed"),
                a_sig.get("ground_attempted"),
            ))
            total_rows += 1

            # Fighter B
            b_name = round_data.get("fighter_b", "")
            b_id = fighter_id_map.get(normalize_fighter_name(b_name))
            b_stats = round_data.get("fighter_b_stats", {})
            b_sig = sig_data.get("fighter_b_strikes", {})

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
                b_sig.get("head_landed"),
                b_sig.get("head_attempted"),
                b_sig.get("body_landed"),
                b_sig.get("body_attempted"),
                b_sig.get("leg_landed"),
                b_sig.get("leg_attempted"),
                b_sig.get("distance_landed"),
                b_sig.get("distance_attempted"),
                b_sig.get("clinch_landed"),
                b_sig.get("clinch_attempted"),
                b_sig.get("ground_landed"),
                b_sig.get("ground_attempted"),
            ))
            total_rows += 1

        fights_loaded += 1

    conn.commit()

    # Verificación
    new_count = pd.read_sql("SELECT COUNT(*) as cnt FROM fight_stats", conn).iloc[0, 0]
    round_dist = pd.read_sql(
        "SELECT round, COUNT(*) as cnt FROM fight_stats GROUP BY round ORDER BY round",
        conn
    )

    print()
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Stats antes:  {old_count:,} filas (solo totals, round=1)")
    print(f"Stats ahora:  {new_count:,} filas (round-by-round)")
    print(f"Peleas cargadas: {fights_loaded:,}")
    print(f"Peleas saltadas: {fights_skipped:,}")
    print(f"\nDistribución por round:")
    for _, row in round_dist.iterrows():
        print(f"  Round {int(row['round'])}: {int(row['cnt']):,} filas")

    # Verificar que peleas multi-round existan
    multi_check = pd.read_sql(
        "SELECT fight_id, COUNT(DISTINCT round) as rounds FROM fight_stats GROUP BY fight_id HAVING rounds > 1 LIMIT 5",
        conn
    )
    print(f"\nPeleas con múltiples rounds en BD: {len(pd.read_sql('SELECT fight_id FROM fight_stats GROUP BY fight_id HAVING COUNT(DISTINCT round) > 1', conn))}")

    if len(multi_check) > 0:
        print("Ejemplo de pelea multi-round:")
        sample_id = multi_check.iloc[0]["fight_id"]
        sample = pd.read_sql(
            f"SELECT fighter_name, round, sig_strikes_landed FROM fight_stats WHERE fight_id = '{sample_id}' ORDER BY round, fighter_name",
            conn
        )
        print(sample.to_string(index=False))

    conn.close()
    print(f"\n✅ Listo. Backup en: {BACKUP_PATH}")
    print("Siguiente paso: regenerar features con python run_phase3_features.py")


if __name__ == "__main__":
    main()
