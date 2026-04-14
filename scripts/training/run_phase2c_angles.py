
from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["figure.dpi"] = 150
plt.rcParams["font.family"] = "sans-serif"

CHARTS_DIR = Path("data/exports/charts/angles")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = "db/ufc_predictor.db"


def save_chart(fig, name):
    path = CHARTS_DIR / (name + ".png")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Guardada: " + str(path))


def load_all():
    conn = sqlite3.connect(DB_PATH)
    fighters = pd.read_sql_query("SELECT * FROM fighters", conn)
    events = pd.read_sql_query("SELECT * FROM events", conn)
    fights = pd.read_sql_query("SELECT * FROM fights", conn)
    fight_stats = pd.read_sql_query("SELECT * FROM fight_stats", conn)
    conn.close()
    return fighters, events, fights, fight_stats


def build_fight_records(fights, events, fighters, fight_stats):
    """
    Construye un DataFrame enriquecido con info de ambos peleadores por pelea.
    """
    # Parsear fechas
    events_d = events[["event_id", "date_parsed"]].copy()
    events_d["date_parsed"] = pd.to_datetime(events_d["date_parsed"], errors="coerce")
    fights_e = fights.merge(events_d, on="event_id", how="left")

    # Parsear DOB de fighters
    fighters_info = fighters[["name", "dob", "height_inches", "reach_inches", "weight_lbs", "stance"]].copy()

    def parse_dob(dob_str):
        if not dob_str or str(dob_str) == "nan":
            return None
        for fmt in ["%b %d, %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(str(dob_str).strip(), fmt)
            except ValueError:
                continue
        return None

    fighters_info["dob_parsed"] = fighters_info["dob"].apply(parse_dob)
    fighters_info["dob_parsed"] = pd.to_datetime(fighters_info["dob_parsed"], errors="coerce")

    # Merge info de fighter A
    fights_e = fights_e.merge(
        fighters_info.rename(columns={
            "name": "fighter_a_name",
            "dob_parsed": "dob_a",
            "height_inches": "height_a",
            "reach_inches": "reach_a",
            "weight_lbs": "weight_a",
            "stance": "stance_a"
        }).drop(columns=["dob"]),
        on="fighter_a_name", how="left"
    )

    # Merge info de fighter B
    fights_e = fights_e.merge(
        fighters_info.rename(columns={
            "name": "fighter_b_name",
            "dob_parsed": "dob_b",
            "height_inches": "height_b",
            "reach_inches": "reach_b",
            "weight_lbs": "weight_b",
            "stance": "stance_b"
        }).drop(columns=["dob"]),
        on="fighter_b_name", how="left"
    )

    # Calcular edades al momento de la pelea
    fights_e["age_a"] = (fights_e["date_parsed"] - fights_e["dob_a"]).dt.days / 365.25
    fights_e["age_b"] = (fights_e["date_parsed"] - fights_e["dob_b"]).dt.days / 365.25

    # Diferencias fisicas
    fights_e["height_diff"] = fights_e["height_a"] - fights_e["height_b"]
    fights_e["reach_diff"] = fights_e["reach_a"] - fights_e["reach_b"]
    fights_e["age_diff"] = fights_e["age_a"] - fights_e["age_b"]

    # Quien gano
    fights_e["a_won"] = (fights_e["winner_name"] == fights_e["fighter_a_name"])
    fights_e["b_won"] = (fights_e["winner_name"] == fights_e["fighter_b_name"])

    return fights_e


# ============================================================
# 1. EDAD Y RENDIMIENTO
# ============================================================
def analyze_age(fights_e):
    print("=" * 60)
    print("1. EDAD Y RENDIMIENTO")
    print("=" * 60)

    # Crear registros desde perspectiva de cada peleador
    records = []
    for _, row in fights_e.iterrows():
        if pd.notna(row["age_a"]) and pd.notna(row.get("winner_name")):
            records.append({
                "age": row["age_a"],
                "won": row["a_won"],
                "name": row["fighter_a_name"]
            })
        if pd.notna(row["age_b"]) and pd.notna(row.get("winner_name")):
            records.append({
                "age": row["age_b"],
                "won": row["b_won"],
                "name": row["fighter_b_name"]
            })

    age_df = pd.DataFrame(records)
    age_df = age_df[(age_df["age"] >= 18) & (age_df["age"] <= 50)]

    # Win rate por grupo de edad
    age_df["age_bin"] = pd.cut(age_df["age"], bins=range(18, 52, 2))
    age_wr = age_df.groupby("age_bin", observed=True).agg(
        win_rate=("won", "mean"),
        count=("won", "count")
    ).reset_index()

    print("  Win rate por edad:")
    for _, row in age_wr.iterrows():
        if row["count"] >= 50:
            print("    " + str(row["age_bin"]) + ": " + str(round(row["win_rate"] * 100, 1)) + "% (" + str(int(row["count"])) + " peleas)")

    # Encontrar edad pico
    peak = age_wr[age_wr["count"] >= 50].sort_values("win_rate", ascending=False).iloc[0]
    print("\n  Edad pico: " + str(peak["age_bin"]) + " con " + str(round(peak["win_rate"] * 100, 1)) + "% win rate")
    print()

    # Grafica
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    age_wr_plot = age_wr[age_wr["count"] >= 50]
    axes[0].bar(range(len(age_wr_plot)), age_wr_plot["win_rate"].values, color="#3498db", edgecolor="white")
    axes[0].set_xticks(range(len(age_wr_plot)))
    axes[0].set_xticklabels([str(x) for x in age_wr_plot["age_bin"].values], rotation=45, fontsize=8)
    axes[0].axhline(0.5, color="red", linestyle="--", alpha=0.5)
    axes[0].set_title("Win Rate por Edad")
    axes[0].set_ylabel("Win Rate")
    axes[0].set_ylim(0.3, 0.7)

    # Distribucion de edades
    axes[1].hist(age_df["age"], bins=40, color="#2ecc71", edgecolor="white", alpha=0.85)
    axes[1].set_title("Distribucion de Edades en Peleas")
    axes[1].set_xlabel("Edad")
    axes[1].axvline(age_df["age"].mean(), color="red", linestyle="--",
                     label="Media: " + str(round(age_df["age"].mean(), 1)))
    axes[1].legend()

    fig.tight_layout()
    save_chart(fig, "01_edad_rendimiento")

    # Diferencia de edad y resultado
    age_diff_df = fights_e.dropna(subset=["age_diff", "winner_name"]).copy()
    age_diff_df["age_diff_bin"] = pd.cut(
        age_diff_df["age_diff"],
        bins=[-20, -8, -4, -2, 0, 2, 4, 8, 20],
        labels=["<-8", "-8a-4", "-4a-2", "-2a0", "0a2", "2a4", "4a8", ">8"]
    )
    age_diff_wr = age_diff_df.groupby("age_diff_bin", observed=True)["a_won"].mean()

    print("  Win rate de peleador A segun diferencia de edad (A - B):")
    for group, wr in age_diff_wr.items():
        print("    " + str(group) + " anos: " + str(round(wr * 100, 1)) + "%")
    print()

    fig, ax = plt.subplots(figsize=(10, 5))
    age_diff_wr.plot(kind="bar", ax=ax, color=sns.color_palette("RdYlGn", len(age_diff_wr)))
    ax.set_title("Win Rate segun Diferencia de Edad")
    ax.set_xlabel("Diferencia de Edad (Peleador A - Peleador B)")
    ax.set_ylabel("Win Rate Peleador A")
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.tick_params(axis="x", rotation=0)
    save_chart(fig, "02_diferencia_edad")


# ============================================================
# 2. DIFERENCIA DE ALTURA
# ============================================================
def analyze_height(fights_e):
    print("=" * 60)
    print("2. DIFERENCIA DE ALTURA")
    print("=" * 60)

    height_df = fights_e.dropna(subset=["height_diff", "winner_name"]).copy()
    height_df["height_diff_bin"] = pd.cut(
        height_df["height_diff"],
        bins=[-15, -5, -3, -1, 1, 3, 5, 15],
        labels=["<-5\"", "-5a-3\"", "-3a-1\"", "-1a1\"", "1a3\"", "3a5\"", ">5\""]
    )

    height_wr = height_df.groupby("height_diff_bin", observed=True).agg(
        win_rate=("a_won", "mean"),
        count=("a_won", "count")
    )

    print("  Win rate segun ventaja de altura (A - B):")
    for group, row in height_wr.iterrows():
        print("    " + str(group) + ": " + str(round(row["win_rate"] * 100, 1)) + "% (" + str(int(row["count"])) + " peleas)")
    print()

    fig, ax = plt.subplots(figsize=(10, 5))
    height_wr["win_rate"].plot(kind="bar", ax=ax, color=sns.color_palette("coolwarm", len(height_wr)))
    ax.set_title("Win Rate segun Ventaja de Altura")
    ax.set_xlabel("Diferencia de Altura (Peleador A - Peleador B)")
    ax.set_ylabel("Win Rate Peleador A")
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.tick_params(axis="x", rotation=0)
    save_chart(fig, "03_diferencia_altura")


# ============================================================
# 3. INACTIVIDAD
# ============================================================
def analyze_inactivity(fights_e):
    print("=" * 60)
    print("3. INACTIVIDAD (TIEMPO ENTRE PELEAS)")
    print("=" * 60)

    # Calcular tiempo desde la ultima pelea de cada peleador
    fights_sorted = fights_e.sort_values("date_parsed")

    inactivity_records = []
    fighter_last_fight = {}

    for _, row in fights_sorted.iterrows():
        date = row["date_parsed"]
        if pd.isna(date):
            continue

        for side in ["a", "b"]:
            name = row["fighter_" + side + "_name"]
            won = row[side + "_won"] if pd.notna(row.get("winner_name")) else None

            if name in fighter_last_fight:
                days_off = (date - fighter_last_fight[name]).days
                if days_off > 0:
                    inactivity_records.append({
                        "fighter_name": name,
                        "days_off": days_off,
                        "won": won,
                        "date": date
                    })

            fighter_last_fight[name] = date

    inact_df = pd.DataFrame(inactivity_records)
    inact_df = inact_df[inact_df["won"].notna()]

    # Agrupar inactividad
    inact_df["inactivity_group"] = pd.cut(
        inact_df["days_off"],
        bins=[0, 60, 120, 180, 270, 365, 548, 730, 3000],
        labels=["<2m", "2-4m", "4-6m", "6-9m", "9-12m", "12-18m", "18-24m", ">24m"]
    )

    inact_wr = inact_df.groupby("inactivity_group", observed=True).agg(
        win_rate=("won", "mean"),
        count=("won", "count")
    )

    print("  Win rate segun tiempo de inactividad:")
    for group, row in inact_wr.iterrows():
        print("    " + str(group) + ": " + str(round(row["win_rate"] * 100, 1)) + "% (" + str(int(row["count"])) + " peleas)")
    print()

    # Promedio de inactividad
    print("  Inactividad promedio: " + str(round(inact_df["days_off"].mean(), 0)) + " dias (" + str(round(inact_df["days_off"].mean() / 30, 1)) + " meses)")
    print("  Mediana: " + str(round(inact_df["days_off"].median(), 0)) + " dias")
    print()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    inact_wr["win_rate"].plot(kind="bar", ax=axes[0], color=sns.color_palette("YlOrRd_r", len(inact_wr)))
    axes[0].set_title("Win Rate segun Inactividad")
    axes[0].set_xlabel("Tiempo de Inactividad")
    axes[0].set_ylabel("Win Rate")
    axes[0].axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    axes[0].tick_params(axis="x", rotation=30)

    axes[1].hist(inact_df["days_off"].clip(upper=800), bins=50, color="#9b59b6", edgecolor="white", alpha=0.85)
    axes[1].set_title("Distribucion de Inactividad")
    axes[1].set_xlabel("Dias entre peleas")
    axes[1].axvline(inact_df["days_off"].median(), color="red", linestyle="--",
                     label="Mediana: " + str(int(inact_df["days_off"].median())) + "d")
    axes[1].legend()

    fig.tight_layout()
    save_chart(fig, "04_inactividad")


# ============================================================
# 4. CAMBIOS DE CATEGORIA
# ============================================================
def analyze_weight_changes(fights_e):
    print("=" * 60)
    print("4. CAMBIOS DE CATEGORIA DE PESO")
    print("=" * 60)

    fights_sorted = fights_e.sort_values("date_parsed")
    weight_change_records = []
    fighter_last_wc = {}

    for _, row in fights_sorted.iterrows():
        wc = row["weight_class"]
        if pd.isna(wc):
            continue

        for side in ["a", "b"]:
            name = row["fighter_" + side + "_name"]
            won = row[side + "_won"] if pd.notna(row.get("winner_name")) else None

            if name in fighter_last_wc:
                prev_wc = fighter_last_wc[name]
                changed = prev_wc != wc

                weight_change_records.append({
                    "fighter_name": name,
                    "prev_wc": prev_wc,
                    "curr_wc": wc,
                    "changed": changed,
                    "won": won,
                })

            fighter_last_wc[name] = wc

    wc_df = pd.DataFrame(weight_change_records)
    wc_df = wc_df[wc_df["won"].notna()]

    changed = wc_df[wc_df["changed"] == True]
    stayed = wc_df[wc_df["changed"] == False]

    print("  Peleas despues de cambiar categoria: " + str(len(changed)))
    print("  Peleas en misma categoria: " + str(len(stayed)))
    print()

    if len(changed) > 0:
        print("  Win rate al cambiar de categoria: " + str(round(changed["won"].mean() * 100, 1)) + "%")
    print("  Win rate sin cambiar: " + str(round(stayed["won"].mean() * 100, 1)) + "%")
    print()

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(
        ["Cambio de categoria", "Misma categoria"],
        [changed["won"].mean() * 100 if len(changed) > 0 else 0, stayed["won"].mean() * 100],
        color=["#e74c3c", "#3498db"], edgecolor="white"
    )
    ax.set_title("Win Rate: Cambio de Categoria vs Misma Categoria")
    ax.set_ylabel("Win Rate (%)")
    ax.set_ylim(0, 70)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                str(round(bar.get_height(), 1)) + "%", ha="center", fontsize=11)
    save_chart(fig, "05_cambio_categoria")


# ============================================================
# 5. CALIDAD DE OPONENTES
# ============================================================
def analyze_opponent_quality(fights_e, fighters):
    print("=" * 60)
    print("5. CALIDAD DE OPONENTES")
    print("=" * 60)

    # Calcular win rate de cada peleador
    fighter_wr = fighters[["name", "wins", "losses", "draws"]].copy()
    fighter_wr["total"] = fighter_wr["wins"] + fighter_wr["losses"] + fighter_wr["draws"]
    fighter_wr["win_rate"] = fighter_wr["wins"] / fighter_wr["total"].replace(0, 1)
    wr_map = fighter_wr.set_index("name")["win_rate"].to_dict()

    # Asignar calidad del oponente
    fights_oq = fights_e.copy()
    fights_oq["opp_wr_for_a"] = fights_oq["fighter_b_name"].map(wr_map)
    fights_oq["opp_wr_for_b"] = fights_oq["fighter_a_name"].map(wr_map)

    # Perspectiva de cada peleador
    records = []
    for _, row in fights_oq.iterrows():
        if pd.notna(row.get("winner_name")):
            if pd.notna(row["opp_wr_for_a"]):
                records.append({"opp_wr": row["opp_wr_for_a"], "won": row["a_won"]})
            if pd.notna(row["opp_wr_for_b"]):
                records.append({"opp_wr": row["opp_wr_for_b"], "won": row["b_won"]})

    oq_df = pd.DataFrame(records)

    oq_df["opp_quality"] = pd.cut(
        oq_df["opp_wr"],
        bins=[0, 0.3, 0.45, 0.55, 0.7, 1.01],
        labels=["Malo (<30%)", "Bajo (30-45%)", "Medio (45-55%)", "Bueno (55-70%)", "Elite (>70%)"]
    )

    oq_wr = oq_df.groupby("opp_quality", observed=True).agg(
        win_rate=("won", "mean"),
        count=("won", "count")
    )

    print("  Win rate segun calidad del oponente:")
    for group, row in oq_wr.iterrows():
        print("    vs " + str(group) + ": " + str(round(row["win_rate"] * 100, 1)) + "% (" + str(int(row["count"])) + " peleas)")
    print()

    fig, ax = plt.subplots(figsize=(10, 5))
    oq_wr["win_rate"].plot(kind="bar", ax=ax, color=sns.color_palette("RdYlGn_r", len(oq_wr)))
    ax.set_title("Win Rate segun Calidad del Oponente")
    ax.set_xlabel("Calidad del Oponente (Win Rate)")
    ax.set_ylabel("Win Rate")
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.tick_params(axis="x", rotation=15)
    save_chart(fig, "06_calidad_oponente")


# ============================================================
# 6. VENTAJA DE EXPERIENCIA
# ============================================================
def analyze_experience(fights_e):
    print("=" * 60)
    print("6. VENTAJA DE EXPERIENCIA")
    print("=" * 60)

    fights_sorted = fights_e.sort_values("date_parsed")

    # Contar peleas previas de cada peleador
    fighter_fight_count = {}
    exp_records = []

    for _, row in fights_sorted.iterrows():
        if pd.isna(row.get("winner_name")):
            continue

        name_a = row["fighter_a_name"]
        name_b = row["fighter_b_name"]

        exp_a = fighter_fight_count.get(name_a, 0)
        exp_b = fighter_fight_count.get(name_b, 0)

        exp_records.append({
            "exp_a": exp_a,
            "exp_b": exp_b,
            "exp_diff": exp_a - exp_b,
            "a_won": row["a_won"],
        })

        fighter_fight_count[name_a] = exp_a + 1
        fighter_fight_count[name_b] = exp_b + 1

    exp_df = pd.DataFrame(exp_records)

    # Debutantes
    debuts_a = exp_df[exp_df["exp_a"] == 0]
    debuts_b = exp_df[exp_df["exp_b"] == 0]
    print("  Peleas con debutante como fighter A: " + str(len(debuts_a)) + ", WR: " + str(round(debuts_a["a_won"].mean() * 100, 1)) + "%")
    print("  Peleas con debutante como fighter B: " + str(len(debuts_b)) + ", WR del debutante: " + str(round((1 - debuts_b["a_won"].mean()) * 100, 1)) + "%")
    print()

    # Diferencia de experiencia
    exp_df["exp_diff_bin"] = pd.cut(
        exp_df["exp_diff"],
        bins=[-50, -10, -5, -2, 0, 2, 5, 10, 50],
        labels=["<-10", "-10a-5", "-5a-2", "-2a0", "0a2", "2a5", "5a10", ">10"]
    )

    exp_wr = exp_df.groupby("exp_diff_bin", observed=True).agg(
        win_rate=("a_won", "mean"),
        count=("a_won", "count")
    )

    print("  Win rate segun ventaja de experiencia UFC (A - B):")
    for group, row in exp_wr.iterrows():
        print("    " + str(group) + " peleas: " + str(round(row["win_rate"] * 100, 1)) + "% (" + str(int(row["count"])) + ")")
    print()

    fig, ax = plt.subplots(figsize=(10, 5))
    exp_wr["win_rate"].plot(kind="bar", ax=ax, color=sns.color_palette("coolwarm", len(exp_wr)))
    ax.set_title("Win Rate segun Ventaja de Experiencia UFC")
    ax.set_xlabel("Diferencia de Peleas UFC (A - B)")
    ax.set_ylabel("Win Rate Peleador A")
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.tick_params(axis="x", rotation=0)
    save_chart(fig, "07_experiencia")


# ============================================================
# 7. RENDIMIENTO POR ROUND (CARDIO / PACING)
# ============================================================
def analyze_pacing(fight_stats):
    print("=" * 60)
    print("7. RENDIMIENTO POR ROUND (CARDIO)")
    print("=" * 60)

    # Solo peleas que llegaron a 3+ rounds
    fight_rounds = fight_stats.groupby("fight_id")["round"].max().reset_index()
    fight_rounds.columns = ["fight_id", "max_round"]
    long_fights = fight_rounds[fight_rounds["max_round"] >= 3]["fight_id"]

    stats_long = fight_stats[fight_stats["fight_id"].isin(long_fights)].copy()

    # Promedio de sig strikes por round
    round_avgs = stats_long.groupby("round").agg(
        avg_sig=("sig_strikes_landed", "mean"),
        avg_td=("takedowns_landed", "mean"),
        avg_ctrl=("control_time_seconds", "mean"),
    ).reset_index()

    print("  Promedio de stats por round (peleas de 3+ rounds):")
    for _, row in round_avgs.iterrows():
        print("    Round " + str(int(row["round"])) + ": Sig=" + str(round(row["avg_sig"], 1)) +
              ", TD=" + str(round(row["avg_td"], 2)) +
              ", Ctrl=" + str(round(row["avg_ctrl"], 0)) + "s")
    print()

    # Calcular cambio porcentual R1 vs R3
    if len(round_avgs) >= 3:
        r1_sig = round_avgs[round_avgs["round"] == 1]["avg_sig"].values[0]
        r3_sig = round_avgs[round_avgs["round"] == 3]["avg_sig"].values[0]
        change = (r3_sig - r1_sig) / r1_sig * 100
        print("  Cambio de sig strikes R1 a R3: " + str(round(change, 1)) + "%")
        print()

    # Clasificar peleadores por pacing
    # Calcular ratio R3/R1 de sig strikes por peleador
    pacing_records = []
    for name, group in stats_long.groupby("fighter_name"):
        r1 = group[group["round"] == 1]["sig_strikes_landed"].mean()
        r3 = group[group["round"] == 3]["sig_strikes_landed"].mean()
        fights_count = group["fight_id"].nunique()

        if pd.notna(r1) and pd.notna(r3) and r1 > 0 and fights_count >= 3:
            pacing_records.append({
                "fighter_name": name,
                "r1_avg": r1,
                "r3_avg": r3,
                "pacing_ratio": r3 / r1,
                "fights": fights_count
            })

    pacing_df = pd.DataFrame(pacing_records)

    if len(pacing_df) > 0:
        def classify_pacing(ratio):
            if ratio > 1.15:
                return "Cardio Monster"
            elif ratio > 0.9:
                return "Consistente"
            elif ratio > 0.7:
                return "Declina Leve"
            else:
                return "Se Apaga"

        pacing_df["pacing_class"] = pacing_df["pacing_ratio"].apply(classify_pacing)
        pacing_counts = pacing_df["pacing_class"].value_counts()

        print("  Clasificacion de cardio (peleadores con 3+ peleas de 3+ rounds):")
        for pc, count in pacing_counts.items():
            print("    " + pc + ": " + str(count) + " peleadores")
        print()

        # Top cardio monsters
        top_cardio = pacing_df[pacing_df["fights"] >= 5].nlargest(10, "pacing_ratio")
        print("  Top 10 'Cardio Monsters' (5+ peleas largas):")
        for _, row in top_cardio.iterrows():
            print("    " + row["fighter_name"] + ": R3/R1 ratio=" + str(round(row["pacing_ratio"], 2)) +
                  " (R1=" + str(round(row["r1_avg"], 1)) + ", R3=" + str(round(row["r3_avg"], 1)) + ")")
        print()

        # Top que se apagan
        top_fade = pacing_df[pacing_df["fights"] >= 5].nsmallest(10, "pacing_ratio")
        print("  Top 10 que se 'apagan' (5+ peleas largas):")
        for _, row in top_fade.iterrows():
            print("    " + row["fighter_name"] + ": R3/R1 ratio=" + str(round(row["pacing_ratio"], 2)) +
                  " (R1=" + str(round(row["r1_avg"], 1)) + ", R3=" + str(round(row["r3_avg"], 1)) + ")")
        print()

    # Grafica
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    rounds_to_plot = round_avgs[round_avgs["round"] <= 5]
    axes[0].plot(rounds_to_plot["round"], rounds_to_plot["avg_sig"], "o-", color="#e74c3c", label="Sig Strikes", linewidth=2)
    axes[0].set_title("Promedio de Sig Strikes por Round")
    axes[0].set_xlabel("Round")
    axes[0].set_ylabel("Sig Strikes Promedio")
    axes[0].legend()

    if len(pacing_df) > 0:
        axes[1].hist(pacing_df["pacing_ratio"].clip(0, 3), bins=40, color="#2ecc71", edgecolor="white", alpha=0.85)
        axes[1].axvline(1.0, color="red", linestyle="--", label="Sin cambio (1.0)")
        axes[1].set_title("Distribucion de Pacing Ratio (R3/R1)")
        axes[1].set_xlabel("Ratio R3 / R1")
        axes[1].legend()

    fig.tight_layout()
    save_chart(fig, "08_cardio_pacing")


# ============================================================
# 8. EFICIENCIA (PRECISION VS VOLUMEN)
# ============================================================
def analyze_efficiency(fight_stats, fights):
    print("=" * 60)
    print("8. EFICIENCIA (PRECISION VS VOLUMEN)")
    print("=" * 60)

    # Agregar por pelea
    agg = fight_stats.groupby(["fight_id", "fighter_name"]).agg(
        sig_landed=("sig_strikes_landed", "sum"),
        sig_attempted=("sig_strikes_attempted", "sum"),
        td_landed=("takedowns_landed", "sum"),
        td_attempted=("takedowns_attempted", "sum"),
    ).reset_index()

    agg["strike_accuracy"] = agg["sig_landed"] / agg["sig_attempted"].replace(0, 1)
    agg["td_accuracy"] = agg["td_landed"] / agg["td_attempted"].replace(0, 1)

    # Merge con resultado
    fights_winners = fights[["fight_id", "winner_name"]].copy()
    agg = agg.merge(fights_winners, on="fight_id", how="left")
    agg["won"] = agg["fighter_name"] == agg["winner_name"]

    # Accuracy vs win rate
    agg["acc_bin"] = pd.cut(
        agg["strike_accuracy"],
        bins=[0, 0.3, 0.4, 0.5, 0.6, 0.7, 1.01],
        labels=["<30%", "30-40%", "40-50%", "50-60%", "60-70%", ">70%"]
    )

    acc_wr = agg.groupby("acc_bin", observed=True).agg(
        win_rate=("won", "mean"),
        count=("won", "count"),
        avg_volume=("sig_attempted", "mean")
    )

    print("  Win rate segun precision de golpes:")
    for group, row in acc_wr.iterrows():
        print("    " + str(group) + ": WR=" + str(round(row["win_rate"] * 100, 1)) +
              "%, volumen promedio=" + str(round(row["avg_volume"], 0)) +
              " (" + str(int(row["count"])) + " peleas)")
    print()

    # Volumen vs accuracy scatter
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    acc_wr["win_rate"].plot(kind="bar", ax=axes[0], color=sns.color_palette("YlGn", len(acc_wr)))
    axes[0].set_title("Win Rate segun Precision de Strikes")
    axes[0].set_xlabel("Strike Accuracy")
    axes[0].set_ylabel("Win Rate")
    axes[0].axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    axes[0].tick_params(axis="x", rotation=15)

    # TD accuracy
    td_agg = agg[agg["td_attempted"] > 0].copy()
    td_agg["td_acc_bin"] = pd.cut(
        td_agg["td_accuracy"],
        bins=[0, 0.25, 0.5, 0.75, 1.01],
        labels=["<25%", "25-50%", "50-75%", ">75%"]
    )
    td_wr = td_agg.groupby("td_acc_bin", observed=True)["won"].mean()

    td_wr.plot(kind="bar", ax=axes[1], color=sns.color_palette("Blues", len(td_wr)))
    axes[1].set_title("Win Rate segun Precision de Takedowns")
    axes[1].set_xlabel("Takedown Accuracy")
    axes[1].set_ylabel("Win Rate")
    axes[1].axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    axes[1].tick_params(axis="x", rotation=0)

    fig.tight_layout()
    save_chart(fig, "09_eficiencia")

    # Peleadores mas eficientes
    fighter_eff = agg.groupby("fighter_name").agg(
        avg_accuracy=("strike_accuracy", "mean"),
        avg_volume=("sig_attempted", "mean"),
        fights=("fight_id", "count"),
        win_rate=("won", "mean")
    ).reset_index()

    top_efficient = fighter_eff[(fighter_eff["fights"] >= 8) & (fighter_eff["avg_volume"] >= 40)].nlargest(10, "avg_accuracy")
    print("  Top 10 peleadores mas eficientes (8+ peleas, 40+ intentos promedio):")
    for _, row in top_efficient.iterrows():
        print("    " + row["fighter_name"] + ": accuracy=" + str(round(row["avg_accuracy"] * 100, 1)) +
              "%, volumen=" + str(round(row["avg_volume"], 0)) +
              ", WR=" + str(round(row["win_rate"] * 100, 1)) + "%")
    print()


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("UFC FIGHT PREDICTOR - FASE 2C: ANGULOS ADICIONALES")
    print("=" * 60)
    print()

    print("Cargando datos...")
    fighters, events, fights, fight_stats = load_all()
    print("Datos cargados.\n")

    print("Construyendo registros enriquecidos...")
    fights_e = build_fight_records(fights, events, fighters, fight_stats)
    print("Registros construidos: " + str(len(fights_e)) + " peleas.\n")

    analyze_age(fights_e)
    analyze_height(fights_e)
    analyze_inactivity(fights_e)
    analyze_weight_changes(fights_e)
    analyze_opponent_quality(fights_e, fighters)
    analyze_experience(fights_e)
    analyze_pacing(fight_stats)
    analyze_efficiency(fight_stats, fights)

    print("=" * 60)
    print("ANALISIS DE ANGULOS COMPLETADO")
    print("Graficas en: " + str(CHARTS_DIR.absolute()))
    print("=" * 60)


if __name__ == "__main__":
    main()