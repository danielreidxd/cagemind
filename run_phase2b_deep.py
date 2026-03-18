"""
UFC Fight Predictor — Fase 2B: Análisis Profundo de Patrones

Análisis avanzado de:
1. Clasificación de estilos de pelea (striker / grappler / mixto)
2. Matchups entre estilos (quién le gana a quién)
3. Tendencias de victoria/derrota (KO, sumisión, decisión)
4. Ritmo de pelea (finisher temprano vs peleador de distancia)
5. Rendimiento reciente vs carrera completa
6. Vulnerabilidades específicas (ser sometido, ser noqueado)
7. Estabilidad/consistencia de racha

Uso:
    python run_phase2b_deep.py

Salida:
    - Gráficas en data/exports/charts/deep/
    - Reporte completo en consola
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["figure.dpi"] = 150
plt.rcParams["font.family"] = "sans-serif"

CHARTS_DIR = Path("data/exports/charts/deep")
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


# ============================================================
# UTILIDAD: Construir historial por peleador
# ============================================================
def build_fighter_profiles(fights, fight_stats, events):
    """
    Construye un perfil detallado por peleador basado en todo su historial.
    Cada pelea se analiza desde la perspectiva de cada peleador.
    """
    # Agregar fecha a las peleas
    events_dates = events[["event_id", "date_parsed"]].copy()
    events_dates["date_parsed"] = pd.to_datetime(events_dates["date_parsed"], errors="coerce")
    fights_dated = fights.merge(events_dates, on="event_id", how="left")
    fights_dated = fights_dated.sort_values("date_parsed")

    # Stats agregadas por pelea (sumar todos los rounds)
    agg = fight_stats.groupby(["fight_id", "fighter_name"]).agg(
        kd=("knockdowns", "sum"),
        sig_landed=("sig_strikes_landed", "sum"),
        sig_attempted=("sig_strikes_attempted", "sum"),
        td_landed=("takedowns_landed", "sum"),
        td_attempted=("takedowns_attempted", "sum"),
        sub_att=("submission_attempts", "sum"),
        ctrl_time=("control_time_seconds", "sum"),
        head_landed=("head_landed", "sum"),
        body_landed=("body_landed", "sum"),
        leg_landed=("leg_landed", "sum"),
        distance_landed=("distance_landed", "sum"),
        clinch_landed=("clinch_landed", "sum"),
        ground_landed=("ground_landed", "sum"),
    ).reset_index()

    # Construir registros individuales por pelea por peleador
    records = []

    for _, fight in fights_dated.iterrows():
        fight_id = fight["fight_id"]
        date = fight["date_parsed"]
        method = fight["method"] if pd.notna(fight["method"]) else ""
        rnd = fight["round"]
        winner = fight["winner_name"]

        for side in ["a", "b"]:
            fighter_name = fight["fighter_" + side + "_name"]
            opponent_name = fight["fighter_" + ("b" if side == "a" else "a") + "_name"]

            won = (fighter_name == winner) if pd.notna(winner) else None
            is_draw = fight["is_draw"] == 1
            is_nc = fight["is_no_contest"] == 1

            # Buscar stats de este peleador en esta pelea
            my_stats = agg[(agg["fight_id"] == fight_id) & (agg["fighter_name"] == fighter_name)]
            opp_stats = agg[(agg["fight_id"] == fight_id) & (agg["fighter_name"] == opponent_name)]

            if len(my_stats) == 0:
                continue

            ms = my_stats.iloc[0]
            os_row = opp_stats.iloc[0] if len(opp_stats) > 0 else None

            # Clasificar método
            method_type = classify_method(method)

            # Determinar cómo perdió/ganó
            finish_type = None
            if won is True:
                finish_type = "win_" + method_type
            elif won is False:
                finish_type = "loss_" + method_type
            elif is_draw:
                finish_type = "draw"
            elif is_nc:
                finish_type = "nc"

            records.append({
                "fighter_name": fighter_name,
                "opponent_name": opponent_name,
                "fight_id": fight_id,
                "date": date,
                "won": won,
                "is_draw": is_draw,
                "is_nc": is_nc,
                "method": method,
                "method_type": method_type,
                "finish_type": finish_type,
                "round": rnd,
                "kd": ms["kd"],
                "sig_landed": ms["sig_landed"],
                "sig_attempted": ms["sig_attempted"],
                "td_landed": ms["td_landed"],
                "td_attempted": ms["td_attempted"],
                "sub_att": ms["sub_att"],
                "ctrl_time": ms["ctrl_time"],
                "head_landed": ms["head_landed"],
                "body_landed": ms["body_landed"],
                "leg_landed": ms["leg_landed"],
                "distance_landed": ms["distance_landed"],
                "clinch_landed": ms["clinch_landed"],
                "ground_landed": ms["ground_landed"],
                "opp_kd": os_row["kd"] if os_row is not None else None,
                "opp_sig_landed": os_row["sig_landed"] if os_row is not None else None,
                "opp_td_landed": os_row["td_landed"] if os_row is not None else None,
                "opp_sub_att": os_row["sub_att"] if os_row is not None else None,
                "opp_ctrl_time": os_row["ctrl_time"] if os_row is not None else None,
            })

    return pd.DataFrame(records)


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


# ============================================================
# 1. CLASIFICACIÓN DE ESTILOS
# ============================================================
def analyze_styles(profiles):
    print("=" * 60)
    print("1. CLASIFICACION DE ESTILOS DE PELEA")
    print("=" * 60)

    # Agregar stats promedio por peleador
    fighter_avgs = profiles.groupby("fighter_name").agg(
        num_fights=("fight_id", "count"),
        avg_sig=("sig_landed", "mean"),
        avg_td=("td_landed", "mean"),
        avg_sub=("sub_att", "mean"),
        avg_ctrl=("ctrl_time", "mean"),
        avg_ground=("ground_landed", "mean"),
        avg_distance=("distance_landed", "mean"),
        avg_clinch=("clinch_landed", "mean"),
        total_wins=("won", "sum"),
    ).reset_index()

    # Solo peleadores con 3+ peleas
    fighter_avgs = fighter_avgs[fighter_avgs["num_fights"] >= 3].copy()
    fighter_avgs["win_rate"] = fighter_avgs["total_wins"] / fighter_avgs["num_fights"]

    # Calcular ratios para clasificar estilo
    # Grappling score = (td + sub + ctrl_time_normalizado + ground) relativo a striking
    fighter_avgs["striking_score"] = fighter_avgs["avg_sig"] + fighter_avgs["avg_distance"]
    fighter_avgs["grappling_score"] = (
        fighter_avgs["avg_td"] * 10 +
        fighter_avgs["avg_sub"] * 15 +
        fighter_avgs["avg_ctrl"] / 30 +
        fighter_avgs["avg_ground"]
    )

    # Normalizar scores
    s_max = fighter_avgs["striking_score"].quantile(0.99)
    g_max = fighter_avgs["grappling_score"].quantile(0.99)
    fighter_avgs["striking_norm"] = (fighter_avgs["striking_score"] / s_max).clip(0, 1)
    fighter_avgs["grappling_norm"] = (fighter_avgs["grappling_score"] / g_max).clip(0, 1)

    # Clasificar
    def classify_style(row):
        s = row["striking_norm"]
        g = row["grappling_norm"]
        if s > 0.6 and g < 0.3:
            return "Striker"
        elif g > 0.5 and s < 0.4:
            return "Grappler"
        elif s > 0.4 and g > 0.3:
            return "Mixto"
        elif s <= 0.4 and g <= 0.3:
            return "Low Output"
        else:
            return "Mixto"

    fighter_avgs["style"] = fighter_avgs.apply(classify_style, axis=1)

    style_counts = fighter_avgs["style"].value_counts()
    print("  Distribucion de estilos (peleadores con 3+ peleas):")
    for style, count in style_counts.items():
        wr = fighter_avgs[fighter_avgs["style"] == style]["win_rate"].mean()
        print("    " + style + ": " + str(count) + " peleadores, win rate: " + str(round(wr * 100, 1)) + "%")
    print()

    # Scatter plot striking vs grappling
    fig, ax = plt.subplots(figsize=(10, 8))
    colors_map = {"Striker": "#e74c3c", "Grappler": "#3498db", "Mixto": "#2ecc71", "Low Output": "#95a5a6"}
    for style, color in colors_map.items():
        subset = fighter_avgs[fighter_avgs["style"] == style]
        ax.scatter(subset["striking_norm"], subset["grappling_norm"],
                   c=color, label=style, alpha=0.5, s=20)
    ax.set_xlabel("Striking Score (normalizado)")
    ax.set_ylabel("Grappling Score (normalizado)")
    ax.set_title("Clasificacion de Estilos de Pelea")
    ax.legend()
    ax.set_xlim(0, 1.1)
    ax.set_ylim(0, 1.1)
    save_chart(fig, "01_estilos_scatter")

    # Win rate por estilo
    fig, ax = plt.subplots(figsize=(8, 5))
    style_wr = fighter_avgs.groupby("style")["win_rate"].mean().sort_values(ascending=False)
    style_wr.plot(kind="bar", ax=ax, color=[colors_map.get(s, "gray") for s in style_wr.index])
    ax.set_title("Win Rate Promedio por Estilo de Pelea")
    ax.set_ylabel("Win Rate")
    ax.set_ylim(0, 1)
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.tick_params(axis="x", rotation=0)
    for i, v in enumerate(style_wr.values):
        ax.text(i, v + 0.01, str(round(v * 100, 1)) + "%", ha="center", fontsize=10)
    save_chart(fig, "02_winrate_por_estilo")

    return fighter_avgs


# ============================================================
# 2. MATCHUPS ENTRE ESTILOS
# ============================================================
def analyze_matchups(profiles, fighter_avgs):
    print("=" * 60)
    print("2. MATCHUPS ENTRE ESTILOS")
    print("=" * 60)

    # Añadir estilos a los perfiles
    style_map = fighter_avgs.set_index("fighter_name")["style"].to_dict()
    profiles_styled = profiles.copy()
    profiles_styled["my_style"] = profiles_styled["fighter_name"].map(style_map)
    profiles_styled["opp_style"] = profiles_styled["opponent_name"].map(style_map)

    # Filtrar solo peleas donde ambos tienen estilo clasificado
    matchups = profiles_styled.dropna(subset=["my_style", "opp_style", "won"])
    matchups = matchups[matchups["won"].notna()].copy()

    # Calcular win rate por matchup
    matchup_wr = matchups.groupby(["my_style", "opp_style"]).agg(
        wins=("won", "sum"),
        total=("won", "count")
    ).reset_index()
    matchup_wr["win_rate"] = matchup_wr["wins"] / matchup_wr["total"]

    print("  Win rate por matchup de estilos:")
    pivot = matchup_wr.pivot(index="my_style", columns="opp_style", values="win_rate")
    pivot_count = matchup_wr.pivot(index="my_style", columns="opp_style", values="total")

    for style_a in ["Striker", "Grappler", "Mixto"]:
        for style_b in ["Striker", "Grappler", "Mixto"]:
            if style_a in pivot.index and style_b in pivot.columns:
                wr = pivot.loc[style_a, style_b]
                n = pivot_count.loc[style_a, style_b]
                if pd.notna(wr):
                    print("    " + style_a + " vs " + style_b + ": " + str(round(wr * 100, 1)) + "% (" + str(int(n)) + " peleas)")
    print()

    # Heatmap
    fig, ax = plt.subplots(figsize=(8, 6))
    display_styles = ["Striker", "Grappler", "Mixto", "Low Output"]
    pivot_display = pivot.reindex(index=display_styles, columns=display_styles).astype(float)
    sns.heatmap(pivot_display, annot=True, fmt=".1%", cmap="RdYlGn", center=0.5,
                ax=ax, vmin=0.3, vmax=0.7, linewidths=1, linecolor="white")
    ax.set_title("Win Rate por Matchup de Estilos\n(filas = peleador, columnas = oponente)")
    ax.set_ylabel("Estilo del Peleador")
    ax.set_xlabel("Estilo del Oponente")
    save_chart(fig, "03_matchup_heatmap")


# ============================================================
# 3. TENDENCIAS: CÓMO GANAN Y CÓMO PIERDEN
# ============================================================
def analyze_tendencies(profiles):
    print("=" * 60)
    print("3. TENDENCIAS DE VICTORIA Y DERROTA")
    print("=" * 60)

    # Por peleador: porcentaje de victorias por KO, sub, dec
    fighter_methods = profiles[profiles["won"].notna()].copy()

    wins = fighter_methods[fighter_methods["won"] == True].copy()
    losses = fighter_methods[fighter_methods["won"] == False].copy()

    # Tendencias de victoria
    win_methods = wins.groupby("fighter_name")["method_type"].value_counts().unstack(fill_value=0)
    win_methods["total_wins"] = win_methods.sum(axis=1)
    for col in ["ko", "sub", "dec"]:
        if col in win_methods.columns:
            win_methods["pct_" + col] = win_methods[col] / win_methods["total_wins"]

    # Tendencias de derrota
    loss_methods = losses.groupby("fighter_name")["method_type"].value_counts().unstack(fill_value=0)
    loss_methods["total_losses"] = loss_methods.sum(axis=1)
    for col in ["ko", "sub", "dec"]:
        if col in loss_methods.columns:
            loss_methods["loss_pct_" + col] = loss_methods[col] / loss_methods["total_losses"]

    # Distribución general
    all_wins = wins["method_type"].value_counts()
    all_losses = losses["method_type"].value_counts()

    print("  Como ganan los peleadores (global):")
    for m, c in all_wins.items():
        print("    " + m + ": " + str(c) + " (" + str(round(c / len(wins) * 100, 1)) + "%)")

    print("  Como pierden los peleadores (global):")
    for m, c in all_losses.items():
        print("    " + m + ": " + str(c) + " (" + str(round(c / len(losses) * 100, 1)) + "%)")
    print()

    # Gráfica
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    all_wins.plot(kind="pie", ax=axes[0], autopct="%1.1f%%",
                  colors=["#e74c3c", "#3498db", "#2ecc71", "#95a5a6"], startangle=90)
    axes[0].set_title("Como Ganan")
    axes[0].set_ylabel("")

    all_losses.plot(kind="pie", ax=axes[1], autopct="%1.1f%%",
                    colors=["#e74c3c", "#3498db", "#2ecc71", "#95a5a6"], startangle=90)
    axes[1].set_title("Como Pierden")
    axes[1].set_ylabel("")
    fig.suptitle("Metodos de Victoria vs Derrota", fontsize=14)
    fig.tight_layout()
    save_chart(fig, "04_como_ganan_vs_pierden")

    # Vulnerabilidades: peleadores que pierden mucho por KO o por sub
    print("  Peleadores mas noqueados (5+ derrotas):")
    ko_vulnerable = loss_methods[loss_methods["total_losses"] >= 5].copy()
    if "ko" in ko_vulnerable.columns:
        ko_vulnerable["ko_loss_pct"] = ko_vulnerable["ko"] / ko_vulnerable["total_losses"]
        top_ko_vuln = ko_vulnerable.nlargest(10, "ko_loss_pct")
        for name, row in top_ko_vuln.iterrows():
            print("    " + str(name) + ": " + str(int(row["ko"])) + "/" + str(int(row["total_losses"])) + " derrotas por KO (" + str(round(row["ko_loss_pct"] * 100, 0)) + "%)")
    print()

    print("  Peleadores mas sometidos (5+ derrotas):")
    if "sub" in ko_vulnerable.columns:
        sub_vulnerable = ko_vulnerable.copy()
        sub_vulnerable["sub_loss_pct"] = sub_vulnerable["sub"] / sub_vulnerable["total_losses"]
        top_sub_vuln = sub_vulnerable.nlargest(10, "sub_loss_pct")
        for name, row in top_sub_vuln.iterrows():
            print("    " + str(name) + ": " + str(int(row["sub"])) + "/" + str(int(row["total_losses"])) + " derrotas por submission (" + str(round(row["sub_loss_pct"] * 100, 0)) + "%)")
    print()

    return win_methods, loss_methods


# ============================================================
# 4. RITMO Y TIMING DE PELEAS
# ============================================================
def analyze_timing(profiles):
    print("=" * 60)
    print("4. RITMO Y TIMING DE PELEAS")
    print("=" * 60)

    wins = profiles[(profiles["won"] == True) & (profiles["method_type"] != "dec")].copy()

    # Round de finalización cuando ganan por finish
    print("  Round de finalizacion (solo KO/Sub):")
    round_dist = wins["round"].dropna().astype(int).value_counts().sort_index()
    for r, count in round_dist.items():
        print("    Round " + str(r) + ": " + str(count) + " finalizaciones (" + str(round(count / len(wins) * 100, 1)) + "%)")
    print()

    # Clasificar peleadores por timing
    fighter_timing = profiles[profiles["won"] == True].copy()
    fighter_timing = fighter_timing.groupby("fighter_name").agg(
        total_wins=("won", "count"),
        finishes=("method_type", lambda x: sum(x.isin(["ko", "sub"]))),
        avg_finish_round=("round", "mean"),
        r1_finishes=("round", lambda x: sum(x == 1)),
    ).reset_index()

    fighter_timing = fighter_timing[fighter_timing["total_wins"] >= 3].copy()
    fighter_timing["finish_rate"] = fighter_timing["finishes"] / fighter_timing["total_wins"]
    fighter_timing["r1_rate"] = fighter_timing["r1_finishes"] / fighter_timing["total_wins"]

    # Clasificar
    def classify_timing(row):
        if row["finish_rate"] > 0.7 and row["avg_finish_round"] <= 1.5:
            return "Finisher R1"
        elif row["finish_rate"] > 0.6:
            return "Finisher"
        elif row["finish_rate"] < 0.3:
            return "Decision Fighter"
        else:
            return "Balanced"

    fighter_timing["timing_class"] = fighter_timing.apply(classify_timing, axis=1)

    timing_counts = fighter_timing["timing_class"].value_counts()
    print("  Clasificacion por timing (peleadores con 3+ victorias):")
    for tc, count in timing_counts.items():
        print("    " + tc + ": " + str(count))
    print()

    # Top finishers de R1
    top_r1 = fighter_timing[fighter_timing["total_wins"] >= 5].nlargest(10, "r1_rate")
    print("  Top 10 finishers de Round 1 (5+ victorias):")
    for _, row in top_r1.iterrows():
        print("    " + row["fighter_name"] + ": " + str(int(row["r1_finishes"])) + "/" + str(int(row["total_wins"])) + " victorias en R1 (" + str(round(row["r1_rate"] * 100, 1)) + "%)")
    print()

    # Gráfica
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    timing_counts.plot(kind="bar", ax=axes[0], color=sns.color_palette("Set2", len(timing_counts)))
    axes[0].set_title("Clasificacion por Timing")
    axes[0].set_ylabel("Numero de Peleadores")
    axes[0].tick_params(axis="x", rotation=15)

    round_dist.plot(kind="bar", ax=axes[1], color=sns.color_palette("viridis", len(round_dist)))
    axes[1].set_title("Round de Finalizacion (KO/Sub)")
    axes[1].set_xlabel("Round")
    axes[1].set_ylabel("Finalizaciones")
    axes[1].tick_params(axis="x", rotation=0)

    fig.tight_layout()
    save_chart(fig, "05_timing_peleas")

    return fighter_timing


# ============================================================
# 5. RENDIMIENTO RECIENTE VS CARRERA
# ============================================================
def analyze_recent_form(profiles):
    print("=" * 60)
    print("5. RENDIMIENTO RECIENTE VS CARRERA")
    print("=" * 60)

    # Ordenar por fecha por peleador
    profiles_sorted = profiles.sort_values(["fighter_name", "date"])

    # Calcular win rate de últimas 3 y últimas 5 peleas
    fighter_form = []
    for name, group in profiles_sorted.groupby("fighter_name"):
        if len(group) < 5:
            continue

        group = group.copy()
        group["won_int"] = group["won"].astype(float)

        career_wr = group["won_int"].mean()
        last3_wr = group["won_int"].tail(3).mean()
        last5_wr = group["won_int"].tail(5).mean()

        # Racha actual
        streak = 0
        streak_type = None
        for val in reversed(group["won_int"].values):
            if streak == 0:
                streak_type = "W" if val == 1 else "L"
                streak = 1
            elif (val == 1 and streak_type == "W") or (val == 0 and streak_type == "L"):
                streak += 1
            else:
                break

        fighter_form.append({
            "fighter_name": name,
            "total_fights": len(group),
            "career_wr": career_wr,
            "last3_wr": last3_wr,
            "last5_wr": last5_wr,
            "streak": streak,
            "streak_type": streak_type,
        })

    form_df = pd.DataFrame(fighter_form)

    print("  Peleadores con 5+ peleas: " + str(len(form_df)))
    print("  Win rate promedio carrera: " + str(round(form_df["career_wr"].mean() * 100, 1)) + "%")
    print("  Win rate promedio ultimas 5: " + str(round(form_df["last5_wr"].mean() * 100, 1)) + "%")
    print("  Win rate promedio ultimas 3: " + str(round(form_df["last3_wr"].mean() * 100, 1)) + "%")
    print()

    # Correlación entre forma reciente y carrera
    print("  Correlacion carrera vs reciente:")
    print("    career_wr vs last5_wr: " + str(round(form_df["career_wr"].corr(form_df["last5_wr"]), 3)))
    print("    career_wr vs last3_wr: " + str(round(form_df["career_wr"].corr(form_df["last3_wr"]), 3)))
    print()

    # Rachas
    print("  Distribucion de rachas actuales:")
    streak_dist = form_df.groupby("streak_type")["streak"].describe()
    for st in ["W", "L"]:
        if st in streak_dist.index:
            row = streak_dist.loc[st]
            print("    Racha " + st + ": media=" + str(round(row["mean"], 1)) + ", max=" + str(int(row["max"])))
    print()

    # Top rachas ganadoras
    top_w_streaks = form_df[form_df["streak_type"] == "W"].nlargest(10, "streak")
    print("  Top 10 rachas ganadoras actuales:")
    for _, row in top_w_streaks.iterrows():
        print("    " + row["fighter_name"] + ": " + str(int(row["streak"])) + "W (career WR: " + str(round(row["career_wr"] * 100, 1)) + "%)")
    print()

    # Gráfica
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].scatter(form_df["career_wr"], form_df["last5_wr"], alpha=0.3, s=10, c="#3498db")
    axes[0].plot([0, 1], [0, 1], "r--", alpha=0.5, label="Perfecta correlacion")
    axes[0].set_xlabel("Win Rate Carrera")
    axes[0].set_ylabel("Win Rate Ultimas 5")
    axes[0].set_title("Carrera vs Ultimas 5 Peleas")
    axes[0].legend()

    streak_data = form_df.copy()
    streak_data["signed_streak"] = streak_data.apply(
        lambda r: r["streak"] if r["streak_type"] == "W" else -r["streak"], axis=1
    )
    axes[1].hist(streak_data["signed_streak"], bins=40, color="#e74c3c", edgecolor="white", alpha=0.85)
    axes[1].set_xlabel("Racha (positiva=victorias, negativa=derrotas)")
    axes[1].set_ylabel("Numero de Peleadores")
    axes[1].set_title("Distribucion de Rachas Actuales")
    axes[1].axvline(0, color="navy", linestyle="--")

    fig.tight_layout()
    save_chart(fig, "06_forma_reciente")

    return form_df


# ============================================================
# 6. ESTABILIDAD / CONSISTENCIA
# ============================================================
def analyze_consistency(profiles):
    print("=" * 60)
    print("6. ESTABILIDAD Y CONSISTENCIA")
    print("=" * 60)

    # Calcular varianza en rendimiento por peleador
    profiles_sorted = profiles.sort_values(["fighter_name", "date"])

    consistency = []
    for name, group in profiles_sorted.groupby("fighter_name"):
        if len(group) < 6:
            continue

        group = group.copy()
        group["won_int"] = group["won"].astype(float)

        # Calcular rolling win rate (ventana de 3)
        group["rolling_wr"] = group["won_int"].rolling(3, min_periods=3).mean()

        # Varianza del rolling WR = medida de inconsistencia
        rolling_var = group["rolling_wr"].dropna().var()
        career_wr = group["won_int"].mean()

        # Contar cambios de dirección (W->L o L->W)
        results = group["won_int"].values
        direction_changes = sum(1 for i in range(1, len(results)) if results[i] != results[i-1])
        change_rate = direction_changes / (len(results) - 1)

        consistency.append({
            "fighter_name": name,
            "total_fights": len(group),
            "career_wr": career_wr,
            "rolling_variance": rolling_var,
            "direction_changes": direction_changes,
            "change_rate": change_rate,
        })

    cons_df = pd.DataFrame(consistency)

    # Clasificar estabilidad
    def classify_stability(row):
        if row["change_rate"] > 0.6:
            return "Muy Inestable"
        elif row["change_rate"] > 0.45:
            return "Inestable"
        elif row["change_rate"] > 0.3:
            return "Moderado"
        else:
            return "Consistente"

    cons_df["stability"] = cons_df.apply(classify_stability, axis=1)

    stability_counts = cons_df["stability"].value_counts()
    print("  Clasificacion de estabilidad (peleadores con 6+ peleas):")
    for stab, count in stability_counts.items():
        avg_wr = cons_df[cons_df["stability"] == stab]["career_wr"].mean()
        print("    " + stab + ": " + str(count) + " peleadores, WR promedio: " + str(round(avg_wr * 100, 1)) + "%")
    print()

    # Top peleadores más inestables
    top_unstable = cons_df[(cons_df["stability"] == "Muy Inestable") & (cons_df["total_fights"] >= 8)].nlargest(10, "change_rate")
    print("  Top 10 peleadores mas inestables (8+ peleas):")
    for _, row in top_unstable.iterrows():
        print("    " + row["fighter_name"] + ": " + str(row["direction_changes"]) + " cambios en " + str(row["total_fights"]) + " peleas, WR=" + str(round(row["career_wr"] * 100, 1)) + "%")
    print()

    # Top peleadores más consistentes con buen WR
    top_consistent = cons_df[(cons_df["stability"] == "Consistente") & (cons_df["career_wr"] > 0.7)].nlargest(10, "total_fights")
    print("  Top 10 peleadores mas consistentes (WR>70%):")
    for _, row in top_consistent.iterrows():
        print("    " + row["fighter_name"] + ": " + str(row["direction_changes"]) + " cambios en " + str(row["total_fights"]) + " peleas, WR=" + str(round(row["career_wr"] * 100, 1)) + "%")
    print()

    # Gráfica
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    colors_stab = {"Consistente": "#27ae60", "Moderado": "#f39c12", "Inestable": "#e67e22", "Muy Inestable": "#e74c3c"}
    for stab, color in colors_stab.items():
        subset = cons_df[cons_df["stability"] == stab]
        axes[0].scatter(subset["career_wr"], subset["change_rate"],
                        c=color, label=stab, alpha=0.5, s=15)
    axes[0].set_xlabel("Win Rate Carrera")
    axes[0].set_ylabel("Tasa de Cambio (inestabilidad)")
    axes[0].set_title("Win Rate vs Estabilidad")
    axes[0].legend(fontsize=8)

    stability_counts.plot(kind="bar", ax=axes[1],
                          color=[colors_stab.get(s, "gray") for s in stability_counts.index])
    axes[1].set_title("Distribucion de Estabilidad")
    axes[1].set_ylabel("Numero de Peleadores")
    axes[1].tick_params(axis="x", rotation=15)

    fig.tight_layout()
    save_chart(fig, "07_estabilidad")

    return cons_df


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("UFC FIGHT PREDICTOR - FASE 2B: ANALISIS PROFUNDO")
    print("=" * 60)
    print()

    print("Cargando datos...")
    fighters, events, fights, fight_stats = load_all()
    print("Datos cargados.\n")

    print("Construyendo perfiles de peleadores...")
    print("(esto puede tardar 1-2 minutos)")
    profiles = build_fighter_profiles(fights, fight_stats, events)
    print("Perfiles construidos: " + str(len(profiles)) + " registros.\n")

    # Ejecutar análisis
    fighter_avgs = analyze_styles(profiles)
    analyze_matchups(profiles, fighter_avgs)
    analyze_tendencies(profiles)
    analyze_timing(profiles)
    analyze_recent_form(profiles)
    analyze_consistency(profiles)

    print("=" * 60)
    print("ANALISIS PROFUNDO COMPLETADO")
    print("Graficas en: " + str(CHARTS_DIR.absolute()))
    print("=" * 60)


if __name__ == "__main__":
    main()