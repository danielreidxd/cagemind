
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from collections import defaultdict

import pandas as pd
import numpy as np

SHERDOG_FILE = Path("data/raw/sherdog/fighter_histories.json")
DB_PATH = Path("db/ufc_predictor.db")
OUTPUT_FILE = Path("data/processed/sherdog_features.csv")


def parse_method(method_raw):
    """Parsear método de victoria/derrota de Sherdog."""
    if not method_raw:
        return "unknown"
    m = method_raw.lower()
    if "ko" in m or "tko" in m or "punch" in m or "kick" in m or "knee" in m or "elbow" in m:
        return "ko"
    if "sub" in m or "choke" in m or "armbar" in m or "lock" in m or "triangle" in m or "guillotine" in m:
        return "sub"
    if "dec" in m or "decision" in m:
        return "dec"
    if "draw" in m:
        return "draw"
    if "no contest" in m or "nc" in m:
        return "nc"
    return "other"


def parse_round(rnd_str):
    """Parsear round."""
    try:
        return int(rnd_str)
    except (ValueError, TypeError):
        return None


def process_sherdog_data():
    """Procesar datos de Sherdog y generar features pre-UFC por peleador."""
    print("Cargando datos de Sherdog...")
    with open(SHERDOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Peleadores con datos: {len(data)}")

    features = {}
    total_pre_ufc = 0
    total_valid = 0

    for name, profile in data.items():
        fights = profile.get("fights", [])

        # Filtrar header row y peleas inválidas
        valid_fights = []
        for fight in fights:
            if fight.get("result") in ("result", "", None):
                continue
            if fight.get("opponent") in ("Fighter", "", None):
                continue
            valid_fights.append(fight)

        # Separar pre-UFC y UFC
        pre_ufc = [f for f in valid_fights if not f.get("is_ufc", False)]
        ufc = [f for f in valid_fights if f.get("is_ufc", False)]

        if not pre_ufc:
            continue

        total_pre_ufc += len(pre_ufc)
        total_valid += 1

        # Calcular features pre-UFC
        wins = sum(1 for f in pre_ufc if f["result"] == "win")
        losses = sum(1 for f in pre_ufc if f["result"] == "loss")
        draws = sum(1 for f in pre_ufc if f["result"] == "draw")
        nc = sum(1 for f in pre_ufc if f["result"] not in ("win", "loss", "draw"))
        total = wins + losses + draws

        if total == 0:
            continue

        # Win rate pre-UFC
        pre_ufc_wr = wins / total if total > 0 else 0.5

        # Métodos de victoria
        win_fights = [f for f in pre_ufc if f["result"] == "win"]
        ko_wins = sum(1 for f in win_fights if parse_method(f["method"]) == "ko")
        sub_wins = sum(1 for f in win_fights if parse_method(f["method"]) == "sub")
        dec_wins = sum(1 for f in win_fights if parse_method(f["method"]) == "dec")

        n_wins = len(win_fights) if win_fights else 1
        ko_rate_pre = ko_wins / n_wins
        sub_rate_pre = sub_wins / n_wins
        dec_rate_pre = dec_wins / n_wins
        finish_rate_pre = (ko_wins + sub_wins) / n_wins

        # Métodos de derrota
        loss_fights = [f for f in pre_ufc if f["result"] == "loss"]
        ko_losses = sum(1 for f in loss_fights if parse_method(f["method"]) == "ko")
        sub_losses = sum(1 for f in loss_fights if parse_method(f["method"]) == "sub")
        n_losses = len(loss_fights) if loss_fights else 1
        ko_loss_rate_pre = ko_losses / n_losses if loss_fights else 0
        sub_loss_rate_pre = sub_losses / n_losses if loss_fights else 0

        # Round promedio de finalizacion
        finish_rounds = []
        for f in pre_ufc:
            method = parse_method(f["method"])
            if method in ("ko", "sub"):
                rnd = parse_round(f["round"])
                if rnd:
                    finish_rounds.append(rnd)
        avg_finish_rnd_pre = np.mean(finish_rounds) if finish_rounds else None

        # Experiencia total (pre + UFC)
        total_pro_fights = len(valid_fights)

        # Racha entrando a UFC (últimas peleas pre-UFC)
        streak_pre = 0
        for f in pre_ufc:
            if f["result"] == "win":
                streak_pre += 1
            elif f["result"] == "loss":
                streak_pre = -1
                break
            else:
                break

        # Nivel de competencia (organizaciones)
        orgs = set()
        for f in pre_ufc:
            event = f.get("event", "")
            # Detectar organizaciones mayores
            e_lower = event.lower()
            if "bellator" in e_lower:
                orgs.add("bellator")
            elif "one" in e_lower and "championship" in e_lower:
                orgs.add("one")
            elif "pfl" in e_lower:
                orgs.add("pfl")
            elif "invicta" in e_lower:
                orgs.add("invicta")
            elif "cage warriors" in e_lower:
                orgs.add("cage_warriors")
            elif "lfa" in e_lower:
                orgs.add("lfa")
            elif "combate" in e_lower:
                orgs.add("combate")
            elif "ksw" in e_lower:
                orgs.add("ksw")
            elif "rizin" in e_lower:
                orgs.add("rizin")

        # Score de nivel de organizacion (0-1)
        major_orgs = {"bellator", "one", "pfl", "rizin", "ksw"}
        mid_orgs = {"invicta", "cage_warriors", "lfa", "combate"}
        org_level = 0.0
        if orgs & major_orgs:
            org_level = 0.8
        elif orgs & mid_orgs:
            org_level = 0.5
        elif orgs:
            org_level = 0.3
        else:
            org_level = 0.2

        features[name] = {
            "pre_ufc_fights": len(pre_ufc),
            "pre_ufc_wins": wins,
            "pre_ufc_losses": losses,
            "pre_ufc_draws": draws,
            "pre_ufc_wr": round(pre_ufc_wr, 4),
            "pre_ufc_ko_rate": round(ko_rate_pre, 4),
            "pre_ufc_sub_rate": round(sub_rate_pre, 4),
            "pre_ufc_dec_rate": round(dec_rate_pre, 4),
            "pre_ufc_finish_rate": round(finish_rate_pre, 4),
            "pre_ufc_ko_loss_rate": round(ko_loss_rate_pre, 4),
            "pre_ufc_sub_loss_rate": round(sub_loss_rate_pre, 4),
            "pre_ufc_avg_finish_round": round(avg_finish_rnd_pre, 2) if avg_finish_rnd_pre else None,
            "pre_ufc_streak": streak_pre,
            "total_pro_fights": total_pro_fights,
            "org_level": org_level,
            "ufc_fights_sherdog": len(ufc),
        }

    print(f"Peleadores con peleas pre-UFC: {total_valid}")
    print(f"Total peleas pre-UFC procesadas: {total_pre_ufc}")

    return features


def save_to_db(features):
    """Guardar features de Sherdog en SQLite."""
    conn = sqlite3.connect(str(DB_PATH))

    # Crear tabla
    conn.execute("DROP TABLE IF EXISTS sherdog_features")
    conn.execute("""
        CREATE TABLE sherdog_features (
            name TEXT PRIMARY KEY,
            pre_ufc_fights INTEGER,
            pre_ufc_wins INTEGER,
            pre_ufc_losses INTEGER,
            pre_ufc_draws INTEGER,
            pre_ufc_wr REAL,
            pre_ufc_ko_rate REAL,
            pre_ufc_sub_rate REAL,
            pre_ufc_dec_rate REAL,
            pre_ufc_finish_rate REAL,
            pre_ufc_ko_loss_rate REAL,
            pre_ufc_sub_loss_rate REAL,
            pre_ufc_avg_finish_round REAL,
            pre_ufc_streak INTEGER,
            total_pro_fights INTEGER,
            org_level REAL,
            ufc_fights_sherdog INTEGER
        )
    """)

    for name, feat in features.items():
        conn.execute("""
            INSERT OR REPLACE INTO sherdog_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            name,
            feat["pre_ufc_fights"], feat["pre_ufc_wins"], feat["pre_ufc_losses"],
            feat["pre_ufc_draws"], feat["pre_ufc_wr"],
            feat["pre_ufc_ko_rate"], feat["pre_ufc_sub_rate"], feat["pre_ufc_dec_rate"],
            feat["pre_ufc_finish_rate"],
            feat["pre_ufc_ko_loss_rate"], feat["pre_ufc_sub_loss_rate"],
            feat["pre_ufc_avg_finish_round"], feat["pre_ufc_streak"],
            feat["total_pro_fights"], feat["org_level"],
            feat["ufc_fights_sherdog"],
        ))

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM sherdog_features").fetchone()[0]
    print(f"\nGuardado en BD: {count} peleadores en tabla sherdog_features")
    conn.close()


def save_to_csv(features):
    """Guardar como CSV."""
    df = pd.DataFrame.from_dict(features, orient="index")
    df.index.name = "name"
    df.to_csv(OUTPUT_FILE)
    print(f"Guardado CSV: {OUTPUT_FILE} ({len(df)} filas)")


def print_stats(features):
    """Imprimir estadísticas interesantes."""
    df = pd.DataFrame.from_dict(features, orient="index")

    print("\n" + "=" * 60)
    print("ESTADISTICAS DE DATOS SHERDOG")
    print("=" * 60)
    print(f"  Peleadores con datos:     {len(df)}")
    print(f"  Peleas pre-UFC total:     {df['pre_ufc_fights'].sum()}")
    print(f"  Promedio peleas pre-UFC:  {df['pre_ufc_fights'].mean():.1f}")
    print(f"  Mediana peleas pre-UFC:   {df['pre_ufc_fights'].median():.0f}")
    print(f"  Max peleas pre-UFC:       {df['pre_ufc_fights'].max()}")
    print(f"  Win rate pre-UFC prom:    {df['pre_ufc_wr'].mean():.3f}")
    print(f"  Finish rate pre-UFC prom: {df['pre_ufc_finish_rate'].mean():.3f}")
    print(f"  Org level promedio:       {df['org_level'].mean():.2f}")

    # Top 10 con mas peleas pre-UFC
    top = df.nlargest(10, "pre_ufc_fights")
    print("\n  Top 10 con mas peleas pre-UFC:")
    for name, row in top.iterrows():
        print(f"    {name}: {int(row['pre_ufc_fights'])} peleas ({row['pre_ufc_wr']:.0%} WR)")

    # Peleadores de orgs mayores
    major = df[df["org_level"] >= 0.8]
    print(f"\n  Peleadores de orgs mayores (Bellator/ONE/PFL): {len(major)}")


def main():
    print("=" * 60)
    print("INTEGRACION DE DATOS SHERDOG A CAGEMIND")
    print("=" * 60)

    features = process_sherdog_data()
    save_to_db(features)
    save_to_csv(features)
    print_stats(features)

    print("\n" + "=" * 60)
    print("SIGUIENTE PASO: Re-correr Feature Engineering y Model Training")
    print("  1. El script run_phase3_features.py ahora puede usar sherdog_features")
    print("  2. Luego re-entrenar con run_phase4_model.py")
    print("=" * 60)


if __name__ == "__main__":
    main()