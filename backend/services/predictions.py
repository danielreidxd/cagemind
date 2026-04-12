"""
Servicio de predicciones: calibración, features en vivo, confianza.
"""
from __future__ import annotations

import numpy as np
from fastapi import HTTPException

from backend.config import PROB_CAP, COMPRESSION, MIN_UFC_FIGHTS_FOR_RELIABLE
from backend.database import get_db, load_models, load_fighter_cache, load_fighter_stats_cache
from backend.services.fighters import get_fight_history, compute_features_for_fighter


# ============================================================
# CALIBRACIÓN DE PROBABILIDADES
# ============================================================

def calibrate_proba(prob_a: float, prob_b: float) -> tuple[float, float]:
    """
    Calibra probabilidades binarias para hacerlas más realistas.
    1. Comprime hacia 50% usando el factor COMPRESSION.
    2. Aplica cap duro de PROB_CAP.
    3. Re-normaliza para que sumen 1.0.
    """
    # Paso 1: Comprimir hacia 0.5
    ca = 0.5 + (prob_a - 0.5) * COMPRESSION
    cb = 0.5 + (prob_b - 0.5) * COMPRESSION

    # Paso 2: Aplicar cap
    ca = min(ca, PROB_CAP)
    cb = min(cb, PROB_CAP)

    # Paso 3: Re-normalizar para que sumen 1.0
    total = ca + cb
    ca = ca / total
    cb = cb / total

    return round(ca, 4), round(cb, 4)


# ============================================================
# FEATURE COMPUTATION (para predicciones en vivo)
# ============================================================

def compute_live_features(name_a: str, name_b: str) -> np.ndarray:
    """
    Calcula las features para una predicción en vivo.
    Usa los datos más recientes disponibles de ambos peleadores.
    """
    bundle = load_models()
    feature_names = bundle["feature_names"]
    fighters = load_fighter_cache()
    stats = load_fighter_stats_cache()

    # Obtener info de ambos peleadores
    info_a = fighters.get(name_a)
    info_b = fighters.get(name_b)

    if not info_a:
        raise HTTPException(status_code=404, detail="Peleador no encontrado: " + name_a)
    if not info_b:
        raise HTTPException(status_code=404, detail="Peleador no encontrado: " + name_b)

    stats_a = stats.get(name_a, {})
    stats_b = stats.get(name_b, {})

    # Obtener historial de peleas para cada peleador
    conn = get_db()

    hist_a = get_fight_history(conn, name_a)
    hist_b = get_fight_history(conn, name_b)

    conn.close()

    # Calcular features para cada peleador
    feats_a = compute_features_for_fighter(info_a, stats_a, hist_a)
    feats_b = compute_features_for_fighter(info_b, stats_b, hist_b)

    # Agregar features de Sherdog (pre-UFC) con descuento por experiencia UFC
    try:
        conn2 = get_db()
        sherdog_a = conn2.execute(
            "SELECT * FROM sherdog_features WHERE name = ?", (name_a,)
        ).fetchone()
        sherdog_b = conn2.execute(
            "SELECT * FROM sherdog_features WHERE name = ?", (name_b,)
        ).fetchone()

        # Contar peleas UFC para calcular descuento
        ufc_fights_a = conn2.execute(
            "SELECT COUNT(*) FROM fights WHERE fighter_a_name = ? OR fighter_b_name = ?",
            (name_a, name_a)
        ).fetchone()[0]
        ufc_fights_b = conn2.execute(
            "SELECT COUNT(*) FROM fights WHERE fighter_a_name = ? OR fighter_b_name = ?",
            (name_b, name_b)
        ).fetchone()[0]
        conn2.close()

        # Factor de descuento: 1.0 (sin UFC) → 0.3 (5+ peleas UFC)
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
        pass  # Si no existe la tabla, seguir sin Sherdog

    # Construir vector de features en el orden correcto
    feature_vector = []
    for fname in feature_names:
        if fname.startswith("a_"):
            key = fname[2:]
            feature_vector.append(feats_a.get(key, 0) or 0)
        elif fname.startswith("b_"):
            key = fname[2:]
            feature_vector.append(feats_b.get(key, 0) or 0)
        elif fname.startswith("diff_"):
            key = fname[5:]
            va = feats_a.get(key, 0) or 0
            vb = feats_b.get(key, 0) or 0
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


# ============================================================
# DETECCIÓN DE NEWCOMERS + CONFIDENCE SCORE
# ============================================================

def assess_data_quality(name_a: str, name_b: str) -> dict:
    """
    Evalúa la calidad de datos de ambos peleadores.
    Retorna confidence level (HIGH/MEDIUM/LOW) y score numérico.
    """
    conn = get_db()

    fights_a = conn.execute(
        "SELECT COUNT(*) FROM fights WHERE fighter_a_name = ? OR fighter_b_name = ?",
        (name_a, name_a)
    ).fetchone()[0]

    fights_b = conn.execute(
        "SELECT COUNT(*) FROM fights WHERE fighter_a_name = ? OR fighter_b_name = ?",
        (name_b, name_b)
    ).fetchone()[0]

    fighters = load_fighter_cache()
    info_a = fighters.get(name_a, {})
    info_b = fighters.get(name_b, {})
    has_stats_a = (info_a.get("slpm") or 0) > 0
    has_stats_b = (info_b.get("slpm") or 0) > 0

    has_sherdog_a = False
    has_sherdog_b = False
    try:
        sherdog_a = conn.execute(
            "SELECT pre_ufc_fights FROM sherdog_features WHERE name = ?", (name_a,)
        ).fetchone()
        sherdog_b = conn.execute(
            "SELECT pre_ufc_fights FROM sherdog_features WHERE name = ?", (name_b,)
        ).fetchone()
        has_sherdog_a = sherdog_a is not None and (sherdog_a[0] or 0) > 0
        has_sherdog_b = sherdog_b is not None and (sherdog_b[0] or 0) > 0
    except Exception:
        pass

    conn.close()

    is_newcomer_a = fights_a < MIN_UFC_FIGHTS_FOR_RELIABLE
    is_newcomer_b = fights_b < MIN_UFC_FIGHTS_FOR_RELIABLE

    score_a = min(fights_a / 5, 1.0) * 0.4 + (0.3 if has_stats_a else 0) + (0.15 if has_sherdog_a else 0)
    score_b = min(fights_b / 5, 1.0) * 0.4 + (0.3 if has_stats_b else 0) + (0.15 if has_sherdog_b else 0)
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
            reason = f"{newcomer} tiene pocas peleas UFC ({min(fights_a, fights_b)})"
        else:
            reason = "Datos limitados para uno o ambos peleadores"
    else:
        confidence = "LOW"
        if is_newcomer_a and is_newcomer_b:
            reason = f"Ambos tienen muy pocas peleas UFC ({fights_a} y {fights_b})"
        elif is_newcomer_a or is_newcomer_b:
            newcomer = name_a if is_newcomer_a else name_b
            n_fights = fights_a if is_newcomer_a else fights_b
            reason = f"{newcomer} tiene {n_fights} peleas UFC - prediccion poco confiable"
        else:
            reason = "Datos insuficientes"

    return {
        "confidence": confidence,
        "confidence_score": round(combined_score, 3),
        "is_newcomer_a": is_newcomer_a,
        "is_newcomer_b": is_newcomer_b,
        "ufc_fights_a": fights_a,
        "ufc_fights_b": fights_b,
        "reason": reason,
    }


def apply_newcomer_adjustment(prob_a: float, prob_b: float, quality: dict) -> tuple:
    """
    Comprime probabilidades hacia 50/50 cuando hay datos insuficientes.
    HIGH confidence = sin cambio. LOW = máxima compresión.
    """
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
