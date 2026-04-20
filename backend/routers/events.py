"""
Router de eventos: históricos y upcoming.
"""
from __future__ import annotations

import json as _json
from datetime import datetime, date, timedelta
from pathlib import Path
from functools import lru_cache

from fastapi import APIRouter, Query

from backend.config import VALUE_THRESHOLD
from backend.database import get_db, load_models, load_fighter_cache
from backend.services.predictions import (
    calibrate_proba, compute_live_features, assess_data_quality, apply_newcomer_adjustment,
)
from backend.services.explainability import explain_prediction
from backend.services.odds import fetch_odds, normalize_name, match_fighter_names, american_to_prob
from db.db_helpers import param

router = APIRouter()

# Cache para el archivo de upcoming (evita leer disco cada vez)
_upcoming_events_cache = None
_upcoming_cache_time = None


def get_cached_upcoming_events():
    """Retorna eventos upcoming con cache de 5 minutos."""
    global _upcoming_events_cache, _upcoming_cache_time
    
    now = datetime.now()
    if _upcoming_events_cache is None or _upcoming_cache_time is None:
        return None
    
    if (now - _upcoming_cache_time).total_seconds() > 300:  # 5 minutos
        return None
    
    return _upcoming_events_cache


@router.get("/events")
async def get_events(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=1, ge=1, le=1),
):
    """
    Retorna eventos paginados (1 por página para navegación tipo libro).
    Incluye todas las peleas con predicciones retroactivas y resultados reales.
    """
    conn = get_db()
    p = param()  # Usar placeholder correcto según BD

    # Total de eventos
    result = conn.execute("""
        SELECT COUNT(*) FROM events e
        WHERE e.date_parsed IS NOT NULL
        AND EXISTS (SELECT 1 FROM fights f WHERE f.event_id = e.event_id)
    """).fetchone()
    total = result[0] if isinstance(result, tuple) else result["count"]

    # Obtener el evento de esta página (ordenado por fecha desc)
    offset = (page - 1)
    event_row = conn.execute(f"""
        SELECT e.event_id, e.name, e.date_parsed, e.location
        FROM events e
        WHERE e.date_parsed IS NOT NULL
        AND EXISTS (SELECT 1 FROM fights f WHERE f.event_id = e.event_id)
        ORDER BY e.date_parsed DESC
        LIMIT 1 OFFSET {p}
    """, (offset,)).fetchone()

    if not event_row:
        conn.close()
        return {"total_events": total, "page": page, "event": None, "fights": []}

    event = dict(event_row)

    # Obtener peleas de este evento
    fight_rows = conn.execute(f"""
        SELECT f.fight_id, f.fighter_a_name, f.fighter_b_name,
               f.winner_name, f.method, f.round, f.time,
               f.weight_class, f.is_draw, f.is_no_contest
        FROM fights f
        WHERE f.event_id = {p}
    """, (event["event_id"],)).fetchall()

    conn.close()

    # Generar predicciones retroactivas para cada pelea
    fighters = load_fighter_cache()
    fights_with_predictions = []

    for fight_row in fight_rows:
        fight = dict(fight_row)
        fa = fight["fighter_a_name"]
        fb = fight["fighter_b_name"]

        # Intentar predecir
        pred = None
        try:
            if fa in fighters and fb in fighters:
                X = compute_live_features(fa, fb)
                bundle = load_models()
                quality = assess_data_quality(fa, fb)

                winner_proba = bundle["winner_model"].predict_proba(X)[0]
                raw_a = float(winner_proba[1])
                raw_b = float(winner_proba[0])
                prob_a, prob_b = calibrate_proba(raw_a, raw_b)
                prob_a, prob_b = apply_newcomer_adjustment(prob_a, prob_b, quality)
                predicted_winner = fa if prob_a > prob_b else fb

                method_proba = bundle["method_model"].predict_proba(X)[0]
                method_classes = list(bundle["method_encoder"].classes_)
                method_dict = {}
                for cls, prob in zip(method_classes, method_proba):
                    label = {"ko": "KO/TKO", "sub": "Submission", "dec": "Decision"}.get(cls, cls)
                    method_dict[label] = round(float(prob), 4)

                event_explanations = explain_prediction(X, predicted_winner, fa, fb, bundle)

                pred = {
                    "predicted_winner": predicted_winner,
                    "prob_a": prob_a,
                    "prob_b": prob_b,
                    "confidence": quality["confidence"],
                    "confidence_score": quality["confidence_score"],
                    "explanations": [e["reason"] for e in event_explanations],
                    "method_prediction": method_dict,
                    "correct": predicted_winner == fight["winner_name"] if fight["winner_name"] else None,
                }
        except Exception:
            pass

        fights_with_predictions.append({
            "fighter_a": fa,
            "fighter_b": fb,
            "winner": fight["winner_name"],
            "method": fight["method"],
            "round": fight["round"],
            "time": fight["time"],
            "weight_class": fight["weight_class"],
            "is_draw": fight["is_draw"],
            "is_no_contest": fight["is_no_contest"],
            "prediction": pred,
        })

    # Calcular accuracy del modelo para este evento
    predictions_made = [f for f in fights_with_predictions if f["prediction"] and f["prediction"]["correct"] is not None]
    correct = sum(1 for f in predictions_made if f["prediction"]["correct"])
    total_predicted = len(predictions_made)

    return {
        "total_events": total,
        "page": page,
        "total_pages": total,
        "event": event,
        "fights": fights_with_predictions,
        "model_accuracy": {
            "correct": correct,
            "total": total_predicted,
            "percentage": round(correct / total_predicted * 100, 1) if total_predicted > 0 else 0,
        },
    }


@router.get("/upcoming")
async def get_upcoming():
    """
    Retorna eventos próximos (futuros) con predicciones pre-calculadas.
    Filtra automáticamente: solo eventos cuya fecha >= hoy.
    Los eventos pasados se quedan en /events (histórico).
    
    OPTIMIZACIÓN: Usa cache de 1 hora para evitar recalcular predicciones.
    """
    global _upcoming_events_cache, _upcoming_cache_time
    
    # Verificar cache primero
    cached = get_cached_upcoming_events()
    if cached is not None:
        return cached
    
    upcoming_file = Path("data/raw/ufcstats/upcoming_events.json")

    if not upcoming_file.exists():
        return {"events": [], "message": "No hay datos de upcoming. Ejecuta: python scripts/scraping/scrape_upcoming.py"}

    with open(upcoming_file, "r", encoding="utf-8") as f:
        all_events = _json.load(f)

    # Filtrar solo eventos futuros y recientes (fecha >= hoy - 2 dias)
    cutoff_date = date.today() - timedelta(days=2)
    events = []
    for ev in all_events:
        try:
            ev_date = datetime.strptime(ev["date"], "%B %d, %Y").date()
            if ev_date >= cutoff_date:
                events.append(ev)
        except (ValueError, KeyError, TypeError):
            events.append(ev)

    fighters = load_fighter_cache()
    bundle = load_models()

    result_events = []
    for event in events:
        fights_with_pred = []
        for fight in event.get("fights", []):
            fa = fight["fighter_a"]
            fb = fight["fighter_b"]

            pred = None
            try:
                if fa in fighters and fb in fighters:
                    # Predicción SIMPLIFICADA - solo modelo winner
                    X = compute_live_features(fa, fb)
                    quality = assess_data_quality(fa, fb)

                    winner_proba = bundle["winner_model"].predict_proba(X)[0]
                    raw_a = float(winner_proba[1])
                    raw_b = float(winner_proba[0])
                    prob_a, prob_b = calibrate_proba(raw_a, raw_b)
                    prob_a, prob_b = apply_newcomer_adjustment(prob_a, prob_b, quality)
                    predicted_winner = fa if prob_a > prob_b else fb

                    info_a = fighters[fa]
                    info_b = fighters[fb]

                    # Predicción simplificada - sin explainability, sin method/round
                    pred = {
                        "predicted_winner": predicted_winner,
                        "prob_a": prob_a,
                        "prob_b": prob_b,
                        "confidence": quality["confidence"],
                        "confidence_score": quality["confidence_score"],
                        "fighter_a_profile": {
                            "record": str(info_a.get("wins", 0)) + "-" + str(info_a.get("losses", 0)) + "-" + str(info_a.get("draws", 0)),
                            "weight": info_a.get("weight_lbs"),
                            "stance": info_a.get("stance"),
                        },
                        "fighter_b_profile": {
                            "record": str(info_b.get("wins", 0)) + "-" + str(info_b.get("losses", 0)) + "-" + str(info_b.get("draws", 0)),
                            "weight": info_b.get("weight_lbs"),
                            "stance": info_b.get("stance"),
                        },
                    }
            except Exception:
                pass

            fights_with_pred.append({
                "fighter_a": fa,
                "fighter_b": fb,
                "weight_class": fight.get("weight_class"),
                "prediction": pred,
            })

        result_events.append({
            "name": event["name"],
            "date": event["date"],
            "location": event.get("location"),
            "fights": fights_with_pred,
            "total_fights": len(fights_with_pred),
            "predicted_fights": sum(1 for f in fights_with_pred if f["prediction"]),
        })

    # Guardar en cache
    _upcoming_events_cache = {"events": result_events, "total_events": len(result_events)}
    _upcoming_cache_time = datetime.now()

    return _upcoming_events_cache
