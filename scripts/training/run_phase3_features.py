
from __future__ import annotations

import sqlite3
import random
import hashlib
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

DB_PATH = "db/ufc_predictor.db"
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)
np.random.seed(42)


def load_data():
    conn = sqlite3.connect(DB_PATH)
    fighters = pd.read_sql_query("SELECT * FROM fighters", conn)
    events = pd.read_sql_query("SELECT * FROM events", conn)
    fights = pd.read_sql_query("SELECT * FROM fights", conn)
    fight_stats = pd.read_sql_query("SELECT * FROM fight_stats", conn)
    conn.close()
    return fighters, events, fights, fight_stats


def parse_dob(dob_str):
    if not dob_str or str(dob_str) == "nan":
        return None
    for fmt in ["%b %d, %Y", "%B %d, %Y"]:
        try:
            return pd.Timestamp(datetime.strptime(str(dob_str).strip(), fmt))
        except ValueError:
            continue
    return None


def classify_method(method):
    if not method:
        return "unknown"
    m = method.upper()
    if "KO" in m or "TKO" in m:
        return "ko"
    elif "SUB" in m:
        return "sub"
    elif "DEC" in m:
        return "dec"
    else:
        return "other"


def build_training_dataset(fighters, events, fights, fight_stats):
    """
    Construye el dataset de entrenamiento.
    
    Para cada pelea:
    1. Aleatoriza quién es A y quién es B
    2. Calcula features usando SOLO datos de peleas anteriores
    3. Genera targets (quién ganó, cómo, en qué round)
    """
    print("Preparando datos base...")

    # Parsear fechas
    events_d = events[["event_id", "date_parsed"]].copy()
    events_d["date_parsed"] = pd.to_datetime(events_d["date_parsed"], errors="coerce")
    fights_dated = fights.merge(events_d, on="event_id", how="left")
    fights_dated = fights_dated.sort_values("date_parsed").reset_index(drop=True)

    # Parsear DOB
    fighters_info = fighters.copy()
    fighters_info["dob_parsed"] = fighters_info["dob"].apply(parse_dob)

    # Indexar fighters por nombre
    fighters_info = fighters_info.drop_duplicates(subset="name", keep="first")
    fighter_lookup = fighters_info.set_index("name").to_dict("index")

    # Agregar stats por pelea (sumar rounds)
    print("Agregando stats por pelea...")
    agg_stats = fight_stats.groupby(["fight_id", "fighter_name"]).agg(
        rounds_fought=("round", "max"),
        kd=("knockdowns", "sum"),
        sig_landed=("sig_strikes_landed", "sum"),
        sig_attempted=("sig_strikes_attempted", "sum"),
        total_landed=("total_strikes_landed", "sum"),
        total_attempted=("total_strikes_attempted", "sum"),
        td_landed=("takedowns_landed", "sum"),
        td_attempted=("takedowns_attempted", "sum"),
        sub_att=("submission_attempts", "sum"),
        reversals=("reversals", "sum"),
        ctrl_time=("control_time_seconds", "sum"),
        head_landed=("head_landed", "sum"),
        head_attempted=("head_attempted", "sum"),
        body_landed=("body_landed", "sum"),
        body_attempted=("body_attempted", "sum"),
        leg_landed=("leg_landed", "sum"),
        leg_attempted=("leg_attempted", "sum"),
        distance_landed=("distance_landed", "sum"),
        distance_attempted=("distance_attempted", "sum"),
        clinch_landed=("clinch_landed", "sum"),
        clinch_attempted=("clinch_attempted", "sum"),
        ground_landed=("ground_landed", "sum"),
        ground_attempted=("ground_attempted", "sum"),
    ).reset_index()

    # Stats por round para cardio
    round_stats = fight_stats[["fight_id", "fighter_name", "round", "sig_strikes_landed"]].copy()

    # Construir historial cronológico por peleador
    print("Construyendo historiales cronologicos...")
    fighter_histories = {}  # nombre -> lista de dicts ordenada por fecha

    for _, fight in fights_dated.iterrows():
        fight_id = fight["fight_id"]
        date = fight["date_parsed"]
        method = fight.get("method", "")
        method_type = classify_method(method)
        rnd = fight.get("round")
        winner = fight.get("winner_name")
        is_draw = fight.get("is_draw", 0) == 1
        is_nc = fight.get("is_no_contest", 0) == 1
        weight_class = fight.get("weight_class")

        for side, opp_side in [("fighter_a_name", "fighter_b_name"), ("fighter_b_name", "fighter_a_name")]:
            name = fight[side]
            opp_name = fight[opp_side]

            won = None
            if not is_draw and not is_nc and pd.notna(winner):
                won = (name == winner)

            my_stats = agg_stats[(agg_stats["fight_id"] == fight_id) & (agg_stats["fighter_name"] == name)]
            opp_stats_row = agg_stats[(agg_stats["fight_id"] == fight_id) & (agg_stats["fighter_name"] == opp_name)]

            # Round stats para cardio
            my_round_stats = round_stats[(round_stats["fight_id"] == fight_id) & (round_stats["fighter_name"] == name)]

            record = {
                "fight_id": fight_id,
                "date": date,
                "opponent": opp_name,
                "won": won,
                "method_type": method_type,
                "round": rnd,
                "is_draw": is_draw,
                "is_nc": is_nc,
                "weight_class": weight_class,
                "stats": my_stats.iloc[0].to_dict() if len(my_stats) > 0 else None,
                "opp_stats": opp_stats_row.iloc[0].to_dict() if len(opp_stats_row) > 0 else None,
                "round_stats": my_round_stats.to_dict("records") if len(my_round_stats) > 0 else [],
            }

            if name not in fighter_histories:
                fighter_histories[name] = []
            fighter_histories[name].append(record)

    # =========================================================
    # CONSTRUIR FEATURES POR PELEA
    # =========================================================
    print("Generando features para cada pelea...")
    dataset = []
    skipped = 0

    for idx, fight in fights_dated.iterrows():
        fight_id = fight["fight_id"]
        date = fight["date_parsed"]
        winner = fight.get("winner_name")
        is_draw = fight.get("is_draw", 0) == 1
        is_nc = fight.get("is_no_contest", 0) == 1
        method = fight.get("method", "")
        method_type = classify_method(method)
        rnd = fight.get("round")
        weight_class = fight.get("weight_class")

        # Saltar peleas sin resultado claro
        if is_draw or is_nc or pd.isna(winner):
            skipped += 1
            continue

        fa_name = fight["fighter_a_name"]
        fb_name = fight["fighter_b_name"]

        # Aleatorizar A y B para eliminar sesgo
        if random.random() > 0.5:
            fa_name, fb_name = fb_name, fa_name

        # Obtener historial PREVIO a esta pelea
        hist_a = get_prior_history(fighter_histories.get(fa_name, []), fight_id, date)
        hist_b = get_prior_history(fighter_histories.get(fb_name, []), fight_id, date)

        # Mínimo 1 pelea previa cada uno
        if len(hist_a) == 0 or len(hist_b) == 0:
            skipped += 1
            continue

        # Calcular features
        feat = {}
        feat["fight_id"] = fight_id
        feat["date"] = date
        feat["fighter_a"] = fa_name
        feat["fighter_b"] = fb_name
        feat["weight_class"] = weight_class

        # Features de A y B
        feats_a = compute_fighter_features(fa_name, hist_a, fighter_lookup, date)
        feats_b = compute_fighter_features(fb_name, hist_b, fighter_lookup, date)

        # Features absolutas de cada peleador
        for key, val in feats_a.items():
            feat["a_" + key] = val
        for key, val in feats_b.items():
            feat["b_" + key] = val

        # Features diferenciales (A - B)
        diff_keys = [
            "age", "height", "reach",
            "career_sig_landed_pm", "career_sig_acc", "career_sig_absorbed_pm", "career_sig_def",
            "career_td_landed_pm", "career_td_acc", "career_td_def", "career_sub_avg",
            "career_kd_pm", "career_ctrl_pm",
            "recent_sig_landed_pm", "recent_sig_acc", "recent_td_landed_pm", "recent_kd_pm",
            "finish_rate", "ko_rate", "sub_rate", "dec_rate",
            "ko_loss_rate", "sub_loss_rate",
            "experience", "win_rate", "recent_win_rate",
            "striking_score", "grappling_score",
            "avg_opp_wr",
            "strike_efficiency", "td_efficiency",
            "cardio_ratio",
        ]
        for key in diff_keys:
            va = feats_a.get(key)
            vb = feats_b.get(key)
            if va is not None and vb is not None:
                feat["diff_" + key] = va - vb
            else:
                feat["diff_" + key] = None

        # Matchup features
        feat["style_matchup"] = get_style_matchup(feats_a, feats_b)

        # === TARGETS ===
        feat["target_winner"] = 1 if winner == fa_name else 0
        feat["target_method"] = method_type
        feat["target_round"] = rnd
        feat["target_goes_distance"] = 1 if method_type == "dec" else 0

        dataset.append(feat)

        if (idx + 1) % 1000 == 0:
            print("  Procesadas " + str(idx + 1) + "/" + str(len(fights_dated)) + " peleas...")

    print("  Peleas procesadas: " + str(len(dataset)))
    print("  Peleas saltadas: " + str(skipped) + " (sin resultado claro o sin historial)")

    return pd.DataFrame(dataset)


def get_prior_history(history, fight_id, date):
    """Retorna solo las peleas ANTERIORES a la pelea actual."""
    prior = []
    for h in history:
        if h["fight_id"] == fight_id:
            continue
        if pd.notna(h["date"]) and pd.notna(date) and h["date"] < date:
            prior.append(h)
    return prior


def safe_div(a, b, default=None):
    if b is None or b == 0 or a is None:
        return default
    return a / b


def compute_fighter_features(name, history, fighter_lookup, fight_date):
    """
    Calcula todas las features de un peleador basándose en su historial previo.
    """
    feat = {}
    n = len(history)
    feat["experience"] = n

    # === FÍSICAS ===
    info = fighter_lookup.get(name, {})
    feat["height"] = info.get("height_inches")
    feat["reach"] = info.get("reach_inches")
    feat["weight"] = info.get("weight_lbs")

    dob = info.get("dob_parsed")
    if pd.notna(dob) and pd.notna(fight_date):
        feat["age"] = (fight_date - dob).days / 365.25
    else:
        feat["age"] = None

    stance = info.get("stance")
    feat["is_orthodox"] = 1 if stance == "Orthodox" else 0
    feat["is_southpaw"] = 1 if stance == "Southpaw" else 0
    feat["is_switch"] = 1 if stance == "Switch" else 0

    # === HISTORIAL GENERAL ===
    wins = sum(1 for h in history if h["won"] is True)
    losses = sum(1 for h in history if h["won"] is False)
    feat["win_rate"] = safe_div(wins, wins + losses, 0.5)
    feat["wins"] = wins
    feat["losses"] = losses

    # === RACHA ===
    streak = 0
    streak_type = None
    for h in reversed(history):
        if h["won"] is None:
            continue
        if streak == 0:
            streak_type = "W" if h["won"] else "L"
            streak = 1
        elif (h["won"] and streak_type == "W") or (not h["won"] and streak_type == "L"):
            streak += 1
        else:
            break
    feat["streak"] = streak if streak_type == "W" else -streak
    feat["abs_streak"] = streak

    # === ESTABILIDAD ===
    results = [h["won"] for h in history if h["won"] is not None]
    if len(results) >= 4:
        changes = sum(1 for i in range(1, len(results)) if results[i] != results[i - 1])
        feat["stability"] = 1 - (changes / (len(results) - 1))
    else:
        feat["stability"] = None

    # === CAREER STATS (promedio por minuto de todas las peleas) ===
    stats_list = [h["stats"] for h in history if h["stats"] is not None]
    opp_stats_list = [h["opp_stats"] for h in history if h["opp_stats"] is not None]

    if len(stats_list) > 0:
        total_rounds = sum(s.get("rounds_fought", 1) or 1 for s in stats_list)
        total_time = total_rounds * 5  # 5 minutos por round

        feat["career_sig_landed_pm"] = safe_div(sum(s.get("sig_landed", 0) or 0 for s in stats_list), total_time, 0)
        feat["career_sig_attempted_pm"] = safe_div(sum(s.get("sig_attempted", 0) or 0 for s in stats_list), total_time, 0)
        feat["career_sig_acc"] = safe_div(
            sum(s.get("sig_landed", 0) or 0 for s in stats_list),
            sum(s.get("sig_attempted", 0) or 0 for s in stats_list), 0)
        feat["career_td_landed_pm"] = safe_div(sum(s.get("td_landed", 0) or 0 for s in stats_list), total_time, 0)
        feat["career_td_attempted_pm"] = safe_div(sum(s.get("td_attempted", 0) or 0 for s in stats_list), total_time, 0)
        feat["career_td_acc"] = safe_div(
            sum(s.get("td_landed", 0) or 0 for s in stats_list),
            sum(s.get("td_attempted", 0) or 0 for s in stats_list), 0)
        feat["career_sub_avg"] = safe_div(sum(s.get("sub_att", 0) or 0 for s in stats_list), total_time, 0)
        feat["career_kd_pm"] = safe_div(sum(s.get("kd", 0) or 0 for s in stats_list), total_time, 0)
        feat["career_ctrl_pm"] = safe_div(sum(s.get("ctrl_time", 0) or 0 for s in stats_list), total_time, 0)

        # Absorbed y defensa
        if len(opp_stats_list) > 0:
            feat["career_sig_absorbed_pm"] = safe_div(
                sum(s.get("sig_landed", 0) or 0 for s in opp_stats_list), total_time, 0)
            opp_sig_att = sum(s.get("sig_attempted", 0) or 0 for s in opp_stats_list)
            opp_sig_land = sum(s.get("sig_landed", 0) or 0 for s in opp_stats_list)
            feat["career_sig_def"] = 1 - safe_div(opp_sig_land, opp_sig_att, 0)
            opp_td_att = sum(s.get("td_attempted", 0) or 0 for s in opp_stats_list)
            opp_td_land = sum(s.get("td_landed", 0) or 0 for s in opp_stats_list)
            feat["career_td_def"] = 1 - safe_div(opp_td_land, opp_td_att, 0)
        else:
            feat["career_sig_absorbed_pm"] = None
            feat["career_sig_def"] = None
            feat["career_td_def"] = None

        # Zona y posición (porcentajes)
        total_sig = sum(s.get("sig_landed", 0) or 0 for s in stats_list)
        feat["pct_head"] = safe_div(sum(s.get("head_landed", 0) or 0 for s in stats_list), total_sig, 0)
        feat["pct_body"] = safe_div(sum(s.get("body_landed", 0) or 0 for s in stats_list), total_sig, 0)
        feat["pct_leg"] = safe_div(sum(s.get("leg_landed", 0) or 0 for s in stats_list), total_sig, 0)
        feat["pct_distance"] = safe_div(sum(s.get("distance_landed", 0) or 0 for s in stats_list), total_sig, 0)
        feat["pct_clinch"] = safe_div(sum(s.get("clinch_landed", 0) or 0 for s in stats_list), total_sig, 0)
        feat["pct_ground"] = safe_div(sum(s.get("ground_landed", 0) or 0 for s in stats_list), total_sig, 0)

        # Eficiencia
        feat["strike_efficiency"] = feat["career_sig_acc"]
        feat["td_efficiency"] = feat["career_td_acc"]
    else:
        for k in ["career_sig_landed_pm", "career_sig_attempted_pm", "career_sig_acc",
                   "career_td_landed_pm", "career_td_attempted_pm", "career_td_acc",
                   "career_sub_avg", "career_kd_pm", "career_ctrl_pm",
                   "career_sig_absorbed_pm", "career_sig_def", "career_td_def",
                   "pct_head", "pct_body", "pct_leg", "pct_distance", "pct_clinch", "pct_ground",
                   "strike_efficiency", "td_efficiency"]:
            feat[k] = None

    # === RECENT STATS (últimas 5 peleas) ===
    recent = history[-5:] if len(history) >= 5 else history
    recent_stats = [h["stats"] for h in recent if h["stats"] is not None]

    if len(recent_stats) > 0:
        r_rounds = sum(s.get("rounds_fought", 1) or 1 for s in recent_stats)
        r_time = r_rounds * 5

        feat["recent_sig_landed_pm"] = safe_div(sum(s.get("sig_landed", 0) or 0 for s in recent_stats), r_time, 0)
        feat["recent_sig_acc"] = safe_div(
            sum(s.get("sig_landed", 0) or 0 for s in recent_stats),
            sum(s.get("sig_attempted", 0) or 0 for s in recent_stats), 0)
        feat["recent_td_landed_pm"] = safe_div(sum(s.get("td_landed", 0) or 0 for s in recent_stats), r_time, 0)
        feat["recent_kd_pm"] = safe_div(sum(s.get("kd", 0) or 0 for s in recent_stats), r_time, 0)
    else:
        feat["recent_sig_landed_pm"] = None
        feat["recent_sig_acc"] = None
        feat["recent_td_landed_pm"] = None
        feat["recent_kd_pm"] = None

    recent_wins = sum(1 for h in recent if h["won"] is True)
    recent_total = sum(1 for h in recent if h["won"] is not None)
    feat["recent_win_rate"] = safe_div(recent_wins, recent_total, 0.5)

    # === MÉTODO DE VICTORIA/DERROTA (tendencias) ===
    win_fights = [h for h in history if h["won"] is True]
    loss_fights = [h for h in history if h["won"] is False]
    n_wins = len(win_fights)
    n_losses = len(loss_fights)

    feat["finish_rate"] = safe_div(
        sum(1 for h in win_fights if h["method_type"] in ["ko", "sub"]), n_wins, 0)
    feat["ko_rate"] = safe_div(sum(1 for h in win_fights if h["method_type"] == "ko"), n_wins, 0)
    feat["sub_rate"] = safe_div(sum(1 for h in win_fights if h["method_type"] == "sub"), n_wins, 0)
    feat["dec_rate"] = safe_div(sum(1 for h in win_fights if h["method_type"] == "dec"), n_wins, 0)

    feat["ko_loss_rate"] = safe_div(sum(1 for h in loss_fights if h["method_type"] == "ko"), n_losses, 0)
    feat["sub_loss_rate"] = safe_div(sum(1 for h in loss_fights if h["method_type"] == "sub"), n_losses, 0)
    feat["dec_loss_rate"] = safe_div(sum(1 for h in loss_fights if h["method_type"] == "dec"), n_losses, 0)

    # Round promedio de finalización
    finish_rounds = [h["round"] for h in win_fights if h["method_type"] in ["ko", "sub"] and h["round"] is not None]
    feat["avg_finish_round"] = np.mean(finish_rounds) if len(finish_rounds) > 0 else None

    # === INACTIVIDAD ===
    if len(history) > 0 and pd.notna(history[-1]["date"]) and pd.notna(fight_date):
        feat["days_inactive"] = (fight_date - history[-1]["date"]).days
    else:
        feat["days_inactive"] = None

    # === ESTILO SCORES ===
    if feat.get("career_sig_landed_pm") is not None:
        feat["striking_score"] = (feat.get("career_sig_landed_pm", 0) or 0) + \
                                  safe_div(feat.get("pct_distance", 0), 1, 0) * 2
        feat["grappling_score"] = (feat.get("career_td_landed_pm", 0) or 0) * 10 + \
                                   (feat.get("career_sub_avg", 0) or 0) * 15 + \
                                   (feat.get("career_ctrl_pm", 0) or 0) + \
                                   safe_div(feat.get("pct_ground", 0), 1, 0) * 3
    else:
        feat["striking_score"] = None
        feat["grappling_score"] = None

    # === CARDIO (R3/R1 ratio) ===
    r1_sigs = []
    r3_sigs = []
    for h in history:
        for rs in h.get("round_stats", []):
            if rs.get("round") == 1 and rs.get("sig_strikes_landed") is not None:
                r1_sigs.append(rs["sig_strikes_landed"])
            elif rs.get("round") == 3 and rs.get("sig_strikes_landed") is not None:
                r3_sigs.append(rs["sig_strikes_landed"])

    if len(r1_sigs) >= 2 and len(r3_sigs) >= 2:
        r1_avg = np.mean(r1_sigs)
        r3_avg = np.mean(r3_sigs)
        feat["cardio_ratio"] = safe_div(r3_avg, r1_avg, 1.0)
    else:
        feat["cardio_ratio"] = None

    # === CALIDAD DE OPONENTES ===
    opp_wrs = []
    for h in history:
        opp = h["opponent"]
        opp_info = fighter_lookup.get(opp, {})
        opp_w = opp_info.get("wins", 0) or 0
        opp_l = opp_info.get("losses", 0) or 0
        if opp_w + opp_l > 0:
            opp_wrs.append(opp_w / (opp_w + opp_l))
    feat["avg_opp_wr"] = np.mean(opp_wrs) if len(opp_wrs) > 0 else None

    # Cambio de categoría
    if len(history) >= 1:
        last_wc = history[-1].get("weight_class")
        # Se determina al comparar en el loop principal
        feat["last_weight_class"] = last_wc
    else:
        feat["last_weight_class"] = None

    return feat


def get_style_matchup(feats_a, feats_b):
    """
    Genera un indicador numérico del matchup de estilos.
    Positivo = A tiene ventaja de estilo, Negativo = B.
    """
    sa = feats_a.get("striking_score")
    ga = feats_a.get("grappling_score")
    sb = feats_b.get("striking_score")
    gb = feats_b.get("grappling_score")

    if any(v is None for v in [sa, ga, sb, gb]):
        return None

    # Grappler vs Striker = ventaja grappler (+)
    # Si A es más grappler y B más striker, A tiene ventaja
    a_grapple_lean = ga - sa
    b_grapple_lean = gb - sb

    return a_grapple_lean - b_grapple_lean


def main():
    print("=" * 60)
    print("UFC FIGHT PREDICTOR - FASE 3: FEATURE ENGINEERING")
    print("=" * 60)
    print()

    fighters, events, fights, fight_stats = load_data()
    print("Datos cargados: " + str(len(fights)) + " peleas, " + str(len(fighters)) + " peleadores\n")

    df = build_training_dataset(fighters, events, fights, fight_stats)

    # Guardar dataset
    output_path = OUTPUT_DIR / "training_dataset.csv"
    df.to_csv(output_path, index=False)
    print("\nDataset guardado: " + str(output_path))

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DEL DATASET")
    print("=" * 60)
    print("  Peleas en dataset: " + str(len(df)))
    print("  Features totales: " + str(len([c for c in df.columns if c.startswith(("a_", "b_", "diff_", "style_"))])))
    print("  Columnas totales: " + str(len(df.columns)))
    print()

    # Balance de targets
    print("  Target winner (1=A gana):")
    print("    " + str(df["target_winner"].value_counts().to_dict()))
    print()
    print("  Target method:")
    print("    " + str(df["target_method"].value_counts().to_dict()))
    print()
    print("  Target goes_distance:")
    print("    " + str(df["target_goes_distance"].value_counts().to_dict()))
    print()

    # Missing values
    feat_cols = [c for c in df.columns if c.startswith(("a_", "b_", "diff_"))]
    missing = df[feat_cols].isnull().sum()
    top_missing = missing[missing > 0].sort_values(ascending=False).head(15)
    if len(top_missing) > 0:
        print("  Top 15 features con valores faltantes:")
        for col, count in top_missing.items():
            pct = count / len(df) * 100
            print("    " + col + ": " + str(count) + " (" + str(round(pct, 1)) + "%)")

    # Correlaciones con target_winner
    print("\n  Top 15 features mas correlacionadas con target_winner:")
    numeric_feats = df[feat_cols].select_dtypes(include=[np.number])
    correlations = numeric_feats.corrwith(df["target_winner"]).abs().sort_values(ascending=False)
    for col, corr in correlations.head(15).items():
        print("    " + col + ": " + str(round(corr, 4)))

    print("\n" + "=" * 60)
    print("FASE 3 COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    main()