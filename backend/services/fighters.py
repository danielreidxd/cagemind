
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from backend.database import get_db
from db.db_helpers import param


def get_fight_history(conn, fighter_name):
    """Obtiene el historial de peleas de un peleador."""
    p = param()  # Usar placeholder correcto según BD
    rows = conn.execute(f"""
        SELECT f.fight_id, f.winner_name, f.method, f.round,
               f.fighter_a_name, f.fighter_b_name,
               e.date_parsed
        FROM fights f
        JOIN events e ON f.event_id = e.event_id
        WHERE f.fighter_a_name = {p} OR f.fighter_b_name = {p}
        ORDER BY e.date_parsed
    """, (fighter_name, fighter_name)).fetchall()
    return [dict(r) for r in rows]


def safe_div(a, b, default=0):
    if b is None or b == 0 or a is None:
        return default
    return a / b


def compute_features_for_fighter(info, stats, history):
    """Calcula todas las features de un peleador."""
    feat = {}
    n = len(history)
    feat["experience"] = n

    # Físicas
    feat["height"] = info.get("height_inches")
    feat["reach"] = info.get("reach_inches")
    feat["weight"] = info.get("weight_lbs")

    # Edad
    dob = info.get("dob")
    if dob:
        for fmt in ["%b %d, %Y", "%B %d, %Y"]:
            try:
                dob_dt = datetime.strptime(str(dob).strip(), fmt)
                feat["age"] = (datetime.now() - dob_dt).days / 365.25
                break
            except ValueError:
                continue
    if "age" not in feat:
        feat["age"] = None

    # Stance
    stance = info.get("stance")
    feat["is_orthodox"] = 1 if stance == "Orthodox" else 0
    feat["is_southpaw"] = 1 if stance == "Southpaw" else 0
    feat["is_switch"] = 1 if stance == "Switch" else 0

    # Win rate
    wins = info.get("wins", 0) or 0
    losses = info.get("losses", 0) or 0
    feat["wins"] = wins
    feat["losses"] = losses
    feat["win_rate"] = safe_div(wins, wins + losses, 0.5)

    # Racha
    streak = 0
    streak_type = None
    for h in reversed(history):
        won = (h.get("winner_name") == info.get("name"))
        if streak == 0:
            streak_type = "W" if won else "L"
            streak = 1
        elif (won and streak_type == "W") or (not won and streak_type == "L"):
            streak += 1
        else:
            break
    feat["streak"] = streak if streak_type == "W" else -streak
    feat["abs_streak"] = streak

    # Estabilidad
    results = []
    for h in history:
        winner = h.get("winner_name")
        if winner:
            results.append(1 if winner == info.get("name") else 0)
    if len(results) >= 4:
        changes = sum(1 for i in range(1, len(results)) if results[i] != results[i-1])
        feat["stability"] = 1 - (changes / (len(results) - 1))
    else:
        feat["stability"] = None

    # Career stats from fighter table
    feat["career_sig_landed_pm"] = info.get("slpm", 0) or 0
    feat["career_sig_acc"] = info.get("str_acc", 0) or 0
    feat["career_sig_absorbed_pm"] = info.get("sapm", 0) or 0
    feat["career_sig_def"] = info.get("str_def", 0) or 0
    feat["career_td_landed_pm"] = info.get("td_avg", 0) or 0
    feat["career_td_acc"] = info.get("td_acc", 0) or 0
    feat["career_td_def"] = info.get("td_def", 0) or 0
    feat["career_sub_avg"] = info.get("sub_avg", 0) or 0

    # Stats from aggregated fight_stats
    total_fights = stats.get("total_fights", 1) or 1
    total_time = total_fights * 15  # Aproximación: 3 rounds x 5 min

    feat["career_kd_pm"] = safe_div(stats.get("total_kd", 0), total_time)
    feat["career_ctrl_pm"] = safe_div(stats.get("total_ctrl", 0), total_time)
    feat["career_sig_attempted_pm"] = safe_div(stats.get("total_sig_attempted", 0), total_time)
    feat["career_td_attempted_pm"] = safe_div(stats.get("total_td_attempted", 0), total_time)

    # Strike distribution
    total_sig = stats.get("total_sig_landed", 0) or 1
    feat["pct_head"] = safe_div(stats.get("total_head", 0), total_sig)
    feat["pct_body"] = safe_div(stats.get("total_body", 0), total_sig)
    feat["pct_leg"] = safe_div(stats.get("total_leg", 0), total_sig)
    feat["pct_distance"] = safe_div(stats.get("total_distance", 0), total_sig)
    feat["pct_clinch"] = safe_div(stats.get("total_clinch", 0), total_sig)
    feat["pct_ground"] = safe_div(stats.get("total_ground", 0), total_sig)

    # Eficiencia
    feat["strike_efficiency"] = feat["career_sig_acc"]
    feat["td_efficiency"] = feat["career_td_acc"]

    # Recent stats (últimas 5 peleas) — aproximación con career stats
    feat["recent_sig_landed_pm"] = feat["career_sig_landed_pm"]
    feat["recent_sig_acc"] = feat["career_sig_acc"]
    feat["recent_td_landed_pm"] = feat["career_td_landed_pm"]
    feat["recent_kd_pm"] = feat["career_kd_pm"]

    # Recent win rate (últimas 5)
    recent_results = results[-5:] if len(results) >= 5 else results
    feat["recent_win_rate"] = np.mean(recent_results) if len(recent_results) > 0 else 0.5

    # Método de victoria/derrota
    win_methods = []
    loss_methods = []
    for h in history:
        method = (h.get("method") or "").upper()
        won = h.get("winner_name") == info.get("name")
        m_type = "dec"
        if "KO" in method or "TKO" in method:
            m_type = "ko"
        elif "SUB" in method:
            m_type = "sub"

        if won:
            win_methods.append(m_type)
        elif h.get("winner_name"):
            loss_methods.append(m_type)

    n_wins = len(win_methods)
    n_losses = len(loss_methods)

    feat["finish_rate"] = safe_div(sum(1 for m in win_methods if m in ["ko", "sub"]), n_wins)
    feat["ko_rate"] = safe_div(sum(1 for m in win_methods if m == "ko"), n_wins)
    feat["sub_rate"] = safe_div(sum(1 for m in win_methods if m == "sub"), n_wins)
    feat["dec_rate"] = safe_div(sum(1 for m in win_methods if m == "dec"), n_wins)
    feat["ko_loss_rate"] = safe_div(sum(1 for m in loss_methods if m == "ko"), n_losses)
    feat["sub_loss_rate"] = safe_div(sum(1 for m in loss_methods if m == "sub"), n_losses)
    feat["dec_loss_rate"] = safe_div(sum(1 for m in loss_methods if m == "dec"), n_losses)

    # Round promedio de finalización
    finish_rounds = [h["round"] for h in history
                     if h.get("winner_name") == info.get("name")
                     and ("KO" in (h.get("method") or "").upper() or "SUB" in (h.get("method") or "").upper())
                     and h.get("round") is not None]
    feat["avg_finish_round"] = np.mean(finish_rounds) if finish_rounds else None

    # Inactividad
    if history:
        last_date = history[-1].get("date_parsed")
        if last_date:
            try:
                last_dt = pd.to_datetime(last_date)
                feat["days_inactive"] = (pd.Timestamp.now() - last_dt).days
            except Exception:
                feat["days_inactive"] = None
        else:
            feat["days_inactive"] = None
    else:
        feat["days_inactive"] = None

    # Estilo scores
    feat["striking_score"] = feat["career_sig_landed_pm"] + feat.get("pct_distance", 0) * 2
    feat["grappling_score"] = (feat["career_td_landed_pm"] * 10 +
                                feat["career_sub_avg"] * 15 +
                                feat["career_ctrl_pm"] +
                                feat.get("pct_ground", 0) * 3)

    # Calidad de oponentes (aproximación con career WR)
    feat["avg_opp_wr"] = 0.5  # Default — se calcularía mejor con historial completo

    # Cardio ratio
    feat["cardio_ratio"] = None

    return feat
