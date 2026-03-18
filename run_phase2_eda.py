"""
UFC Fight Predictor — Fase 2: Análisis Exploratorio de Datos (EDA)

Genera visualizaciones y estadísticas para entender los datos
antes de construir el modelo predictivo.

Uso:
    python run_phase2_eda.py

Requisitos extra (instalar una vez):
    python -m pip install matplotlib seaborn

Salida:
    - Gráficas en data/exports/charts/
    - Reporte de texto en consola
"""
from __future__ import annotations

import sqlite3
import os
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Backend sin GUI para que funcione en cualquier entorno
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración visual
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["figure.dpi"] = 150
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.labelsize"] = 11

# Directorio de salida
CHARTS_DIR = Path("data/exports/charts")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = "db/ufc_predictor.db"


def load_data():
    """Carga todas las tablas relevantes desde SQLite."""
    conn = sqlite3.connect(DB_PATH)

    fighters = pd.read_sql_query("SELECT * FROM fighters", conn)
    events = pd.read_sql_query("SELECT * FROM events", conn)
    fights = pd.read_sql_query("SELECT * FROM fights", conn)
    fight_stats = pd.read_sql_query("SELECT * FROM fight_stats", conn)
    data_quality = pd.read_sql_query("SELECT * FROM data_quality", conn)

    conn.close()
    return fighters, events, fights, fight_stats, data_quality


def save_chart(fig, name):
    """Guarda una gráfica y la cierra."""
    path = CHARTS_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Guardada: {path}")


# ============================================================
# 1. RESUMEN GENERAL
# ============================================================
def analyze_overview(fighters, events, fights, fight_stats, data_quality):
    print("=" * 60)
    print("1. RESUMEN GENERAL DEL DATASET")
    print("=" * 60)
    print(f"  Peleadores:     {len(fighters):,}")
    print(f"  Eventos:        {len(events):,}")
    print(f"  Peleas:         {len(fights):,}")
    print(f"  Fight stats:    {len(fight_stats):,} filas (2 por pelea)")
    print()

    # Data quality
    quality_counts = data_quality["detail_level"].value_counts()
    print("  Calidad de datos:")
    for level, count in quality_counts.items():
        pct = count / len(data_quality) * 100
        print(f"    {level}: {count:,} ({pct:.1f}%)")
    print()

    # Datos faltantes en fighters
    print("  Datos faltantes en fighters:")
    missing_cols = ["height_inches", "reach_inches", "weight_lbs", "stance", "dob"]
    for col in missing_cols:
        null_count = fighters[col].isna().sum()
        pct = null_count / len(fighters) * 100
        print(f"    {col}: {null_count:,} ({pct:.1f}%)")
    print()


# ============================================================
# 2. DISTRIBUCIÓN DE PELEADORES
# ============================================================
def analyze_fighters(fighters):
    print("=" * 60)
    print("2. ANÁLISIS DE PELEADORES")
    print("=" * 60)

    # --- 2a: Distribución por peso ---
    fig, ax = plt.subplots(figsize=(12, 6))
    weight_counts = fighters["weight_lbs"].dropna().astype(int)
    # Agrupar en categorías de peso UFC
    weight_bins = [0, 115, 125, 135, 145, 155, 170, 185, 205, 265, 400]
    weight_labels = ["<115", "SW/FLY", "BW", "FW", "LW", "WW", "MW", "LHW", "HW", ">265"]
    fighters_copy = fighters.copy()
    fighters_copy["weight_class_bin"] = pd.cut(
        fighters_copy["weight_lbs"].dropna(), bins=weight_bins, labels=weight_labels
    )
    wc_counts = fighters_copy["weight_class_bin"].value_counts().sort_index()
    wc_counts.plot(kind="bar", ax=ax, color=sns.color_palette("viridis", len(wc_counts)))
    ax.set_title("Distribuci\u00f3n de Peleadores por Categor\u00eda de Peso")
    ax.set_xlabel("Categor\u00eda de Peso")
    ax.set_ylabel("N\u00famero de Peleadores")
    ax.tick_params(axis="x", rotation=0)
    for i, v in enumerate(wc_counts.values):
        ax.text(i, v + 10, str(v), ha="center", fontsize=9)
    save_chart(fig, "01_distribucion_peso")

    # --- 2b: Stance ---
    fig, ax = plt.subplots(figsize=(8, 6))
    stance_counts = fighters["stance"].dropna().value_counts()
    colors = sns.color_palette("Set2", len(stance_counts))
    ax.pie(stance_counts.values, labels=stance_counts.index, autopct="%1.1f%%",
           colors=colors, startangle=90)
    ax.set_title("Distribuci\u00f3n de Stance")
    print(f"  Stance:")
    for stance, count in stance_counts.items():
        print(f"    {stance}: {count} ({count/len(fighters)*100:.1f}%)")
    save_chart(fig, "02_distribucion_stance")
    print()

    # --- 2c: Altura y Reach ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    height_data = fighters["height_inches"].dropna()
    axes[0].hist(height_data, bins=30, color="#3498db", edgecolor="white", alpha=0.85)
    axes[0].axvline(height_data.mean(), color="red", linestyle="--", label=f"Media: {height_data.mean():.1f}\"")
    axes[0].set_title("Distribuci\u00f3n de Altura")
    axes[0].set_xlabel("Pulgadas")
    axes[0].legend()

    reach_data = fighters["reach_inches"].dropna()
    axes[1].hist(reach_data, bins=30, color="#2ecc71", edgecolor="white", alpha=0.85)
    axes[1].axvline(reach_data.mean(), color="red", linestyle="--", label=f"Media: {reach_data.mean():.1f}\"")
    axes[1].set_title("Distribuci\u00f3n de Reach")
    axes[1].set_xlabel("Pulgadas")
    axes[1].legend()

    fig.tight_layout()
    save_chart(fig, "03_altura_reach")

    print(f"  Altura: media={height_data.mean():.1f}\", mediana={height_data.median():.1f}\", std={height_data.std():.1f}")
    print(f"  Reach:  media={reach_data.mean():.1f}\", mediana={reach_data.median():.1f}\", std={reach_data.std():.1f}")
    print()

    # --- 2d: Récord W/L ---
    fig, ax = plt.subplots(figsize=(10, 6))
    fighters_copy = fighters.copy()
    fighters_copy["total_fights"] = fighters_copy["wins"] + fighters_copy["losses"] + fighters_copy["draws"]
    fighters_copy["win_rate"] = fighters_copy["wins"] / fighters_copy["total_fights"].replace(0, 1)
    active = fighters_copy[fighters_copy["total_fights"] >= 3]  # Al menos 3 peleas
    ax.hist(active["win_rate"], bins=40, color="#e74c3c", edgecolor="white", alpha=0.85)
    ax.axvline(active["win_rate"].mean(), color="navy", linestyle="--",
               label=f"Media: {active['win_rate'].mean():.1%}")
    ax.set_title("Distribuci\u00f3n de Win Rate (peleadores con 3+ peleas)")
    ax.set_xlabel("Win Rate")
    ax.set_ylabel("N\u00famero de Peleadores")
    ax.legend()
    save_chart(fig, "04_win_rate")

    print(f"  Win rate promedio (3+ peleas): {active['win_rate'].mean():.1%}")
    print(f"  Peleadores con 3+ peleas: {len(active):,}")
    print()


# ============================================================
# 3. ANÁLISIS DE PELEAS
# ============================================================
def analyze_fights(fights, events):
    print("=" * 60)
    print("3. AN\u00c1LISIS DE PELEAS")
    print("=" * 60)

    # --- 3a: Métodos de victoria ---
    fig, ax = plt.subplots(figsize=(10, 6))
    # Simplificar métodos
    fights_copy = fights.copy()
    fights_copy["method_simple"] = fights_copy["method"].apply(lambda x: simplify_method(x) if pd.notna(x) else "Desconocido")
    method_counts = fights_copy["method_simple"].value_counts()
    colors = sns.color_palette("coolwarm", len(method_counts))
    method_counts.plot(kind="barh", ax=ax, color=colors)
    ax.set_title("M\u00e9todos de Victoria")
    ax.set_xlabel("N\u00famero de Peleas")
    for i, v in enumerate(method_counts.values):
        ax.text(v + 20, i, f"{v} ({v/len(fights)*100:.1f}%)", va="center", fontsize=9)
    fig.tight_layout()
    save_chart(fig, "05_metodos_victoria")

    print("  M\u00e9todos de victoria:")
    for method, count in method_counts.items():
        print(f"    {method}: {count:,} ({count/len(fights)*100:.1f}%)")
    print()

    # --- 3b: Distribución por round de finalización ---
    fig, ax = plt.subplots(figsize=(10, 5))
    round_counts = fights_copy["round"].dropna().astype(int).value_counts().sort_index()
    round_counts.plot(kind="bar", ax=ax, color=sns.color_palette("viridis", len(round_counts)))
    ax.set_title("Distribuci\u00f3n de Round de Finalizaci\u00f3n")
    ax.set_xlabel("Round")
    ax.set_ylabel("N\u00famero de Peleas")
    ax.tick_params(axis="x", rotation=0)
    for i, v in enumerate(round_counts.values):
        ax.text(i, v + 20, str(v), ha="center", fontsize=9)
    save_chart(fig, "06_round_finalizacion")

    # --- 3c: Peleas por año ---
    fig, ax = plt.subplots(figsize=(14, 5))
    events_copy = events.copy()
    events_copy["date_parsed"] = pd.to_datetime(events_copy["date_parsed"], errors="coerce")
    events_copy["year"] = events_copy["date_parsed"].dt.year

    fights_with_events = fights_copy.merge(
        events_copy[["event_id", "year"]], on="event_id", how="left"
    )
    fights_per_year = fights_with_events["year"].dropna().astype(int).value_counts().sort_index()
    fights_per_year.plot(kind="bar", ax=ax, color="#3498db", edgecolor="white")
    ax.set_title("Peleas por A\u00f1o")
    ax.set_xlabel("A\u00f1o")
    ax.set_ylabel("N\u00famero de Peleas")
    ax.tick_params(axis="x", rotation=45)
    save_chart(fig, "07_peleas_por_ano")

    print(f"  Rango de a\u00f1os: {fights_per_year.index.min()} - {fights_per_year.index.max()}")
    print(f"  A\u00f1o con m\u00e1s peleas: {fights_per_year.idxmax()} ({fights_per_year.max():,})")
    print()

    # --- 3d: Categorías de peso ---
    fig, ax = plt.subplots(figsize=(12, 6))
    wc_counts = fights_copy["weight_class"].value_counts().head(15)
    wc_counts.plot(kind="barh", ax=ax, color=sns.color_palette("Set2", len(wc_counts)))
    ax.set_title("Top 15 Categor\u00edas de Peso (por n\u00famero de peleas)")
    ax.set_xlabel("N\u00famero de Peleas")
    fig.tight_layout()
    save_chart(fig, "08_categorias_peso")

    return fights_with_events


def simplify_method(method):
    """Simplifica los métodos de victoria a categorías principales."""
    if not method:
        return "Desconocido"
    method = method.upper()
    if "KO" in method or "TKO" in method:
        return "KO/TKO"
    elif "SUB" in method:
        return "Submission"
    elif "U-DEC" in method:
        return "Decision Unanime"
    elif "S-DEC" in method:
        return "Decision Split"
    elif "M-DEC" in method:
        return "Decision Majority"
    elif "DEC" in method:
        return "Decision (otra)"
    elif "DRAW" in method or "NC" in method:
        return "Draw/NC"
    elif "OVERTURNED" in method:
        return "Overturned"
    else:
        return method[:30]


# ============================================================
# 4. ANÁLISIS DE FIGHT STATS
# ============================================================
def analyze_fight_stats(fight_stats, fights):
    print("=" * 60)
    print("4. AN\u00c1LISIS DE FIGHT STATS")
    print("=" * 60)

    # Estadísticas descriptivas
    numeric_cols = [
        "knockdowns", "sig_strikes_landed", "sig_strikes_attempted",
        "total_strikes_landed", "total_strikes_attempted",
        "takedowns_landed", "takedowns_attempted",
        "submission_attempts", "control_time_seconds"
    ]

    print("  Estad\u00edsticas por round (promedios):")
    for col in numeric_cols:
        data = fight_stats[col].dropna()
        if len(data) > 0:
            print(f"    {col}: media={data.mean():.2f}, mediana={data.median():.1f}, max={data.max():.0f}")
    print()

    # --- 4a: Distribución de sig strikes por pelea ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ss_data = fight_stats["sig_strikes_landed"].dropna()
    axes[0].hist(ss_data, bins=50, color="#e74c3c", edgecolor="white", alpha=0.85)
    axes[0].set_title("Sig. Strikes Landed por Round")
    axes[0].set_xlabel("Golpes Significativos")
    axes[0].axvline(ss_data.mean(), color="navy", linestyle="--", label=f"Media: {ss_data.mean():.1f}")
    axes[0].legend()

    td_data = fight_stats["takedowns_landed"].dropna()
    axes[1].hist(td_data, bins=20, color="#2ecc71", edgecolor="white", alpha=0.85)
    axes[1].set_title("Takedowns Landed por Round")
    axes[1].set_xlabel("Takedowns")
    axes[1].axvline(td_data.mean(), color="navy", linestyle="--", label=f"Media: {td_data.mean():.1f}")
    axes[1].legend()

    fig.tight_layout()
    save_chart(fig, "09_strikes_takedowns_dist")

    # --- 4b: Sig strikes por zona ---
    fig, ax = plt.subplots(figsize=(8, 6))
    zones = {
        "Cabeza": fight_stats["head_landed"].dropna().sum(),
        "Cuerpo": fight_stats["body_landed"].dropna().sum(),
        "Piernas": fight_stats["leg_landed"].dropna().sum(),
    }
    colors_zones = ["#e74c3c", "#3498db", "#2ecc71"]
    ax.pie(zones.values(), labels=zones.keys(), autopct="%1.1f%%",
           colors=colors_zones, startangle=90, textprops={"fontsize": 12})
    ax.set_title("Golpes Significativos por Zona")
    save_chart(fig, "10_strikes_por_zona")

    total_strikes_zone = sum(zones.values())
    print("  Distribuci\u00f3n de golpes por zona:")
    for zone, count in zones.items():
        print(f"    {zone}: {count:,.0f} ({count/total_strikes_zone*100:.1f}%)")
    print()

    # --- 4c: Sig strikes por posición ---
    fig, ax = plt.subplots(figsize=(8, 6))
    positions = {
        "Distancia": fight_stats["distance_landed"].dropna().sum(),
        "Clinch": fight_stats["clinch_landed"].dropna().sum(),
        "Suelo": fight_stats["ground_landed"].dropna().sum(),
    }
    colors_pos = ["#9b59b6", "#f39c12", "#1abc9c"]
    ax.pie(positions.values(), labels=positions.keys(), autopct="%1.1f%%",
           colors=colors_pos, startangle=90, textprops={"fontsize": 12})
    ax.set_title("Golpes Significativos por Posici\u00f3n")
    save_chart(fig, "11_strikes_por_posicion")

    total_strikes_pos = sum(positions.values())
    print("  Distribuci\u00f3n de golpes por posici\u00f3n:")
    for pos, count in positions.items():
        print(f"    {pos}: {count:,.0f} ({count/total_strikes_pos*100:.1f}%)")
    print()


# ============================================================
# 5. CORRELACIONES Y PATRONES PREDICTIVOS
# ============================================================
def analyze_correlations(fights, fight_stats, fighters):
    print("=" * 60)
    print("5. PATRONES PREDICTIVOS")
    print("=" * 60)

    # Agregar stats por pelea por peleador (sumar rounds)
    agg_stats = fight_stats.groupby(["fight_id", "fighter_name"]).agg(
        total_kd=("knockdowns", "sum"),
        total_sig_landed=("sig_strikes_landed", "sum"),
        total_sig_attempted=("sig_strikes_attempted", "sum"),
        total_td_landed=("takedowns_landed", "sum"),
        total_td_attempted=("takedowns_attempted", "sum"),
        total_sub_att=("submission_attempts", "sum"),
        total_ctrl_time=("control_time_seconds", "sum"),
        total_head=("head_landed", "sum"),
        total_body=("body_landed", "sum"),
        total_leg=("leg_landed", "sum"),
    ).reset_index()

    # Merge con fights para saber quién ganó
    fights_with_winner = fights[["fight_id", "winner_name", "fighter_a_name", "fighter_b_name"]].copy()
    merged = agg_stats.merge(fights_with_winner, on="fight_id", how="inner")
    merged["is_winner"] = (merged["fighter_name"] == merged["winner_name"]).astype(int)

    # Comparar medias ganadores vs perdedores
    print("  Promedios por pelea - Ganadores vs Perdedores:")
    compare_cols = [
        ("total_kd", "Knockdowns"),
        ("total_sig_landed", "Sig Strikes Landed"),
        ("total_td_landed", "Takedowns Landed"),
        ("total_sub_att", "Submission Attempts"),
        ("total_ctrl_time", "Control Time (seg)"),
    ]

    winners = merged[merged["is_winner"] == 1]
    losers = merged[merged["is_winner"] == 0]

    fig, axes = plt.subplots(1, len(compare_cols), figsize=(20, 5))
    for i, (col, label) in enumerate(compare_cols):
        w_mean = winners[col].mean()
        l_mean = losers[col].mean()
        print(f"    {label}: Ganador={w_mean:.2f}, Perdedor={l_mean:.2f}, Ratio={w_mean/(l_mean+0.001):.2f}x")

        axes[i].bar(["Ganador", "Perdedor"], [w_mean, l_mean],
                     color=["#27ae60", "#e74c3c"], edgecolor="white")
        axes[i].set_title(label, fontsize=10)
        axes[i].set_ylabel("Promedio")

    fig.suptitle("Comparaci\u00f3n: Ganadores vs Perdedores", fontsize=14, y=1.02)
    fig.tight_layout()
    save_chart(fig, "12_ganadores_vs_perdedores")
    print()

    # --- Reach advantage y victorias ---
    print("  Ventaja de reach y victorias:")
    fights_reach = fights.copy()

    # Merge reach de fighter A y B
    fighter_reach = fighters[["name", "reach_inches"]].copy()
    fighter_reach = fighter_reach.dropna(subset=["reach_inches"])

    fights_reach = fights_reach.merge(
        fighter_reach.rename(columns={"name": "fighter_a_name", "reach_inches": "reach_a"}),
        on="fighter_a_name", how="left"
    )
    fights_reach = fights_reach.merge(
        fighter_reach.rename(columns={"name": "fighter_b_name", "reach_inches": "reach_b"}),
        on="fighter_b_name", how="left"
    )

    # Filtrar peleas con reach de ambos
    fights_reach = fights_reach.dropna(subset=["reach_a", "reach_b"])
    fights_reach["reach_diff"] = fights_reach["reach_a"] - fights_reach["reach_b"]
    fights_reach["a_won"] = (fights_reach["winner_name"] == fights_reach["fighter_a_name"]).astype(int)

    # Agrupar por ventaja de reach
    fights_reach["reach_adv_group"] = pd.cut(
        fights_reach["reach_diff"],
        bins=[-20, -5, -2, 0, 2, 5, 20],
        labels=["<-5\"", "-5 a -2\"", "-2 a 0\"", "0 a 2\"", "2 a 5\"", ">5\""]
    )
    reach_wr = fights_reach.groupby("reach_adv_group")["a_won"].mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    reach_wr.plot(kind="bar", ax=ax, color=sns.color_palette("RdYlGn", len(reach_wr)))
    ax.set_title("Win Rate del Peleador A seg\u00fan Ventaja de Reach")
    ax.set_xlabel("Ventaja de Reach (Peleador A - Peleador B)")
    ax.set_ylabel("Win Rate")
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.tick_params(axis="x", rotation=0)
    ax.set_ylim(0, 1)
    save_chart(fig, "13_reach_vs_winrate")

    print("  Win rate por ventaja de reach:")
    for group, wr in reach_wr.items():
        print(f"    {group}: {wr:.1%}")
    print()

    # --- Correlación de career stats con victorias ---
    fig, ax = plt.subplots(figsize=(10, 8))
    career_cols = ["slpm", "str_acc", "sapm", "str_def", "td_avg", "td_acc", "td_def", "sub_avg"]
    career_data = fighters[career_cols].dropna()
    if len(career_data) > 100:
        corr_matrix = career_data.corr()
        sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm",
                    center=0, ax=ax, square=True)
        ax.set_title("Correlaci\u00f3n entre Career Stats")
        save_chart(fig, "14_correlacion_career_stats")
    else:
        plt.close(fig)
        print("  (No hay suficientes datos para correlaciones de career stats)")


# ============================================================
# 6. ANOMALÍAS Y VALORES ATÍPICOS
# ============================================================
def analyze_anomalies(fighters, fights, fight_stats):
    print("=" * 60)
    print("6. ANOMAL\u00cdAS Y VALORES AT\u00cdPICOS")
    print("=" * 60)

    # Peleadores con 0 peleas registradas
    fighters_copy = fighters.copy()
    fighters_copy["total_fights"] = fighters_copy["wins"] + fighters_copy["losses"] + fighters_copy["draws"]
    zero_fights = fighters_copy[fighters_copy["total_fights"] == 0]
    print(f"  Peleadores con 0 peleas registradas: {len(zero_fights)}")

    # Peleas sin ganador (draw o NC)
    no_winner = fights[(fights["is_draw"] == 1) | (fights["is_no_contest"] == 1)]
    print(f"  Peleas sin ganador (draw/NC): {len(no_winner)}")

    # Fight stats con valores extremos
    ss_max = fight_stats["sig_strikes_landed"].max()
    ss_max_row = fight_stats.loc[fight_stats["sig_strikes_landed"].idxmax()]
    print(f"  Max sig strikes en un round: {ss_max:.0f} por {ss_max_row['fighter_name']}")

    kd_max = fight_stats["knockdowns"].max()
    kd_max_row = fight_stats.loc[fight_stats["knockdowns"].idxmax()]
    print(f"  Max knockdowns en un round: {kd_max:.0f} por {kd_max_row['fighter_name']}")

    # Peleadores con reach extremo
    reach_data = fighters["reach_inches"].dropna()
    if len(reach_data) > 0:
        print(f"  Reach m\u00ednimo: {reach_data.min():.0f}\"")
        print(f"  Reach m\u00e1ximo: {reach_data.max():.0f}\"")

    print()


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("UFC FIGHT PREDICTOR \u2014 FASE 2: AN\u00c1LISIS EXPLORATORIO")
    print("=" * 60)
    print()

    # Cargar datos
    print("Cargando datos desde SQLite...")
    fighters, events, fights, fight_stats, data_quality = load_data()
    print(f"Datos cargados exitosamente.\n")

    # Ejecutar análisis
    analyze_overview(fighters, events, fights, fight_stats, data_quality)
    analyze_fighters(fighters)
    analyze_fights(fights, events)
    analyze_fight_stats(fight_stats, fights)
    analyze_correlations(fights, fight_stats, fighters)
    analyze_anomalies(fighters, fights, fight_stats)

    print("=" * 60)
    print("EDA COMPLETADO")
    print(f"Gr\u00e1ficas guardadas en: {CHARTS_DIR.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()