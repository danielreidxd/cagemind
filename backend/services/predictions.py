from __future__ import annotations

import numpy as np
from fastapi import HTTPException

from backend.config import PROB_CAP, COMPRESSION, MIN_UFC_FIGHTS_FOR_RELIABLE
from backend.database import get_db, load_models, load_fighter_cache, load_fighter_stats_cache
from backend.services.fighters import get_fight_history, compute_features_for_fighter
from db.db_helpers import param


def calibrate_proba(prob_a: float, prob_b: float) -> tuple[float, float]:
    ca = 0.5 + (prob_a - 0.5) * COMPRESSION
    cb = 0.5 + (prob_b - 0.5) * COMPRESSION
    ca = min(ca, PROB_CAP)
    cb = min(cb, PROB_CAP)
    total = ca + cb
    ca = ca / total
    cb = cb / total
    return round(ca, 4), round(cb, 4)


def compute_live_features(name_a: str, name_b: str) -> np.ndarray:
    bundle = load_models()
    feature_names = bundle["feature_names"]
    fighters = load_fighter_cache()
    stats = load_fighter_stats_cache()

    info_a = fighters.get(name_a)
    info_b = fighters.get(name_b)

    if not info_a:
        raise HTTPException(status_code=404, detail=f"Peleador no encontrado: {name_a}")
    if not info_b:
        raise HTTPException(status_code=404, detail=f"Peleador no encontrado: {name_b}")

    stats_a = stats.get(name_a, {})
    stats_b = stats.get(name_b, {})

    conn = get_db()
    hist_a = get_fight_history(conn, name_a)
    hist_b = get_fight_history(conn, name_b)
    conn.close()

    feats_a = compute_features_for_fighter(info_a, stats_a, hist_a)
    feats_b = compute_features_for_fighter(info_b, stats_b, hist_b)

    try:
        conn2 = get_db()
        p = param()
        sherdog_a = conn2.execute(f"SELECT * FROM sherdog_features WHERE name = {p}", (name_a,)).fetchone()
        sherdog_b = conn2.execute(f"SELECT * FROM sherdog_features WHERE name = {p}", (name_b,)).fetchone()

        ufc_fights_a = conn2.execute(
            f"SELECT COUNT(*) FROM fights WHERE fighter_a_name = {p} OR fighter_b_name = {p}",
            (name_a, name_a)
        ).fetchone()[0]
        ufc_fights_b = conn2.execute(
            f"SELECT COUNT(*) FROM fights WHERE fighter_a_name = {p} OR fighter_b_name = {p}",
            (name_b, name_b)
        ).fetchone()[0]
        conn2.close()

        discount_a = max(0.3, 1.0 - ufc_fights_a * 0.14)
        discount_b = max(0.3, 1.0 - ufc_fights_b * 0.14)

        sherdog_keys = [
            "pre_ufc_fights", "pre_ufc_wr", "pre_ufc_ko_rate", "pre_ufc_sub_rate",
            "pre_ufc_dec_rate", "pre_ufc_finish_rate", "pre_ufc_ko_loss_rate",
            "pre_ufc_sub_loss_rate", "pre_ufc_streak", "total_pro_fights", "org_level",
        ]
        no_discount_keys = {"pre_ufc_fights", "total_pro_fights"}

        if sherdog_a:
            sa = dict(sherdog_a)
            for k in sherdog_keys:
                val = sa.get(k, 0) or 0
                if k not in no_discount_keys:
                    val = val * discount_a
                feats_a[k] = val
        if sherdog_b:
            sb = dict(sherdog_b)
            for k in sherdog_keys:
                val = sb.get(k, 0) or 0
                if k not in no_discount_keys:
                    val = val * discount_b
                feats_b[k] = val
    except Exception:
        pass

    def get_effective_age(age):
        if not age:
            return 30
        if 25 <= age <= 34:
            return 28
        return age

    if "age" in feats_a:
        feats_a["age"] = get_effective_age(feats_a["age"])
    if "age" in feats_b:
        feats_b["age"] = get_effective_age(feats_b["age"])

    feature_vector = []
    for fname in feature_names:
        if fname.startswith("a_"):
            feature_vector.append(feats_a.get(fname[2:], 0) or 0)
        elif fname.startswith("b_"):
            feature_vector.append(feats_b.get(fname[2:], 0) or 0)
        elif fname.startswith("diff_"):
            va = feats_a.get(fname[5:], 0) or 0
            vb = feats_b.get(fname[5:], 0) or 0
            feature_vector.append(va - vb)
        elif fname == "style_matchup":
            sa = feats_a.get("striking_score", 0) or 0
            ga = feats_a.get("grappling_score", 0) or 0
            sb = feats_b.get("striking_score", 0) or 0
            gb = feats_b.get("grappling_score", 0) or 0
            feature_vector.append((ga - sa) - (gb - sb))
        else:
            feature_vector.append(0)

    return np.array(feature_vector).reshape(1, -1)


def assess_data_quality(name_a: str, name_b: str) -> dict:
    """
    Evalúa calidad de datos SIN consultar la BD (usa solo cache en memoria).
    Esto es crítico para rendimiento en endpoints que procesan múltiples peleas.
    """
    fighters = load_fighter_cache()
    stats = load_fighter_stats_cache()
    
    info_a = fighters.get(name_a, {})
    info_b = fighters.get(name_b, {})
    
    # Obtener stats de peleas desde cache
    stats_a = stats.get(name_a, {})
    stats_b = stats.get(name_b, {})
    
    # Aproximar peleas UFC desde career stats
    ufc_fights_a = stats_a.get("total_fights", 0) or 0
    ufc_fights_b = stats_b.get("total_fights", 0) or 0
    
    has_stats_a = (info_a.get("slpm") or 0) > 0
    has_stats_b = (info_b.get("slpm") or 0) > 0

    is_newcomer_a = ufc_fights_a < MIN_UFC_FIGHTS_FOR_RELIABLE
    is_newcomer_b = ufc_fights_b < MIN_UFC_FIGHTS_FOR_RELIABLE

    score_a = min(ufc_fights_a / 5, 1.0) * 0.4 + (0.3 if has_stats_a else 0) + 0.15
    score_b = min(ufc_fights_b / 5, 1.0) * 0.4 + (0.3 if has_stats_b else 0) + 0.15
    combined_score = min(score_a, score_b)

    if score_a > 0.7 and score_b > 0.7:
        combined_score = min(combined_score + 0.15, 1.0)

    if combined_score >= 0.70:
        confidence = "HIGH"
        reason = "Ambos peleadores tienen historial UFC solido"
    elif combined_score >= 0.40:
        confidence = "MEDIUM"
        if is_newcomer_a or is_newcomer_b:
            newcomer = name_a if is_newcomer_a else name_b
            reason = f"{newcomer} tiene pocas peleas UFC ({min(ufc_fights_a, ufc_fights_b)})"
        else:
            reason = "Datos limitados para uno o ambos peleadores"
    else:
        confidence = "LOW"
        if is_newcomer_a and is_newcomer_b:
            reason = f"Ambos tienen muy pocas peleas UFC ({ufc_fights_a} y {ufc_fights_b})"
        elif is_newcomer_a or is_newcomer_b:
            newcomer = name_a if is_newcomer_a else name_b
            n_fights = ufc_fights_a if is_newcomer_a else ufc_fights_b
            reason = f"{newcomer} tiene {n_fights} peleas UFC - prediccion poco confiable"
        else:
            reason = "Datos insuficientes"

    return {
        "confidence": confidence,
        "confidence_score": round(combined_score, 3),
        "is_newcomer_a": is_newcomer_a,
        "is_newcomer_b": is_newcomer_b,
        "ufc_fights_a": ufc_fights_a,
        "ufc_fights_b": ufc_fights_b,
        "reason": reason,
    }


def apply_newcomer_adjustment(prob_a: float, prob_b: float, quality: dict) -> tuple:
    if quality["confidence"] == "HIGH":
        return prob_a, prob_b

    score = quality["confidence_score"]
    compression = max(0, min(1, score / 0.7))

    adj_a = 0.5 + (prob_a - 0.5) * compression
    adj_b = 0.5 + (prob_b - 0.5) * compression

    total = adj_a + adj_b
    adj_a = adj_a / total
    adj_b = adj_b / total

    return round(adj_a, 4), round(adj_b, 4)
