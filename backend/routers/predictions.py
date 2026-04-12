"""
Router de predicciones: sandbox predict endpoint.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.database import load_models, load_fighter_cache
from backend.schemas import PredictionRequest, PredictionResponse
from backend.services.predictions import (
    calibrate_proba, compute_live_features, assess_data_quality, apply_newcomer_adjustment,
)
from backend.services.explainability import explain_prediction

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict_fight(request: PredictionRequest):
    """
    Predice el resultado de una pelea entre dos peleadores.
    Retorna: ganador, probabilidad, método probable, round probable.
    """
    bundle = load_models()
    name_a = request.fighter_a
    name_b = request.fighter_b

    fighters = load_fighter_cache()

    # Validar que existan
    if name_a not in fighters:
        matches = [n for n in fighters if name_a.lower() in n.lower()]
        if len(matches) == 1:
            name_a = matches[0]
        else:
            raise HTTPException(status_code=404,
                                detail="Peleador A no encontrado: " + request.fighter_a +
                                       (". Coincidencias: " + str(matches[:5]) if matches else ""))

    if name_b not in fighters:
        matches = [n for n in fighters if name_b.lower() in n.lower()]
        if len(matches) == 1:
            name_b = matches[0]
        else:
            raise HTTPException(status_code=404,
                                detail="Peleador B no encontrado: " + request.fighter_b +
                                       (". Coincidencias: " + str(matches[:5]) if matches else ""))

    # Calcular features
    X = compute_live_features(name_a, name_b)

    # Evaluar calidad de datos
    quality = assess_data_quality(name_a, name_b)

    # === Modelo 1: Quién gana ===
    winner_model = bundle["winner_model"]
    winner_proba = winner_model.predict_proba(X)[0]
    raw_a = float(winner_proba[1])  # P(A gana) raw
    raw_b = float(winner_proba[0])  # P(B gana) raw
    prob_a, prob_b = calibrate_proba(raw_a, raw_b)
    prob_a, prob_b = apply_newcomer_adjustment(prob_a, prob_b, quality)
    winner = name_a if prob_a > prob_b else name_b
    winner_prob = max(prob_a, prob_b)
    loser_prob = min(prob_a, prob_b)

    # === Explainable AI: Top 3 razones ===
    explanations = explain_prediction(X, winner, name_a, name_b, bundle)

    # === Modelo 2: Cómo gana ===
    method_model = bundle["method_model"]
    method_encoder = bundle["method_encoder"]
    method_proba = method_model.predict_proba(X)[0]
    method_classes = list(method_encoder.classes_)
    method_dict = {}
    for cls, prob in zip(method_classes, method_proba):
        label = {"ko": "KO/TKO", "sub": "Submission", "dec": "Decision"}.get(cls, cls)
        method_dict[label] = round(float(prob), 4)

    # === Modelo 3: Llega a decisión ===
    distance_model = bundle["distance_model"]
    dist_proba = distance_model.predict_proba(X)[0]
    distance_dict = {
        "finish": round(float(dist_proba[0]), 4),
        "decision": round(float(dist_proba[1]), 4),
    }

    # === Modelo 4: En qué round ===
    round_model = bundle["round_model"]
    round_proba = round_model.predict_proba(X)[0]
    round_labels = ["Round 1", "Round 2", "Round 3", "Round 4+"]
    round_dict = {}
    for lbl, prob in zip(round_labels, round_proba):
        round_dict[lbl] = round(float(prob), 4)

    # Perfiles resumidos
    info_a = fighters[name_a]
    info_b = fighters[name_b]

    return PredictionResponse(
        fighter_a=name_a,
        fighter_b=name_b,
        winner=winner,
        winner_probability=winner_prob,
        loser_probability=loser_prob,
        method_prediction=method_dict,
        goes_to_decision=distance_dict,
        round_prediction=round_dict,
        fighter_a_profile={
            "name": name_a,
            "record": str(info_a.get("wins", 0)) + "-" + str(info_a.get("losses", 0)) + "-" + str(info_a.get("draws", 0)),
            "height": info_a.get("height_inches"),
            "reach": info_a.get("reach_inches"),
            "weight": info_a.get("weight_lbs"),
            "stance": info_a.get("stance"),
            "win_probability": prob_a,
        },
        fighter_b_profile={
            "name": name_b,
            "record": str(info_b.get("wins", 0)) + "-" + str(info_b.get("losses", 0)) + "-" + str(info_b.get("draws", 0)),
            "height": info_b.get("height_inches"),
            "reach": info_b.get("reach_inches"),
            "weight": info_b.get("weight_lbs"),
            "stance": info_b.get("stance"),
            "win_probability": prob_b,
        },
        confidence=quality["confidence"],
        confidence_score=quality["confidence_score"],
        confidence_reason=quality["reason"],
        explanations=explanations,
    )
