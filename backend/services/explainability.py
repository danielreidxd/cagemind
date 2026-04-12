"""
Explainable AI — Genera razones legibles para las predicciones.
"""
from __future__ import annotations

import numpy as np


# ============================================================
# TRADUCCIONES DE FEATURES
# ============================================================

FEATURE_TRANSLATIONS = {
    "diff_age": "Diferencia de edad",
    "diff_win_rate": "Win rate de carrera",
    "diff_recent_win_rate": "Win rate reciente (ult. 5)",
    "diff_career_td_landed_pm": "Takedowns por minuto",
    "diff_recent_td_landed_pm": "Takedowns recientes/min",
    "diff_career_sig_landed_pm": "Golpes significativos/min",
    "diff_career_sig_absorbed_pm": "Golpes absorbidos/min",
    "diff_career_sig_def": "Defensa de striking",
    "diff_career_sig_acc": "Precision de striking",
    "diff_career_ctrl_pm": "Control time/min",
    "diff_career_kd_pm": "Knockdowns/min",
    "diff_grappling_score": "Habilidad de grappling",
    "diff_striking_score": "Habilidad de striking",
    "diff_experience": "Experiencia UFC",
    "diff_reach": "Ventaja de reach",
    "diff_height": "Ventaja de altura",
    "diff_finish_rate": "Tasa de finalizacion",
    "diff_ko_rate": "Tasa de KO",
    "diff_sub_rate": "Tasa de sumision",
    "diff_stability": "Consistencia/estabilidad",
    "diff_avg_opp_wr": "Calidad de oponentes",
    "diff_pre_ufc_wr": "Win rate pre-UFC",
    "diff_pre_ufc_finish_rate": "Finish rate pre-UFC",
    "diff_pre_ufc_ko_rate": "KO rate pre-UFC",
    "diff_total_pro_fights": "Experiencia profesional total",
    "diff_org_level": "Nivel de organizaciones previas",
    "diff_career_td_acc": "Precision de takedowns",
    "diff_career_td_def": "Defensa de takedowns",
    "diff_recent_sig_landed_pm": "Striking reciente/min",
    "diff_recent_ctrl_pm": "Control reciente/min",
    "diff_days_inactive": "Inactividad",
    "a_age": "Edad",
    "b_age": "Edad",
    "a_win_rate": "Win rate",
    "b_win_rate": "Win rate",
    "a_experience": "Peleas UFC",
    "b_experience": "Peleas UFC",
    "a_stability": "Consistencia",
    "b_stability": "Consistencia",
    "a_career_kd_pm": "Poder de KO",
    "b_career_kd_pm": "Poder de KO",
    "a_career_td_landed_pm": "Takedowns/min",
    "b_career_td_landed_pm": "Takedowns/min",
    "a_career_sig_def": "Defensa de striking",
    "b_career_sig_def": "Defensa de striking",
    "a_recent_win_rate": "Forma reciente",
    "b_recent_win_rate": "Forma reciente",
}


def explain_prediction(X: np.ndarray, winner_name: str, name_a: str, name_b: str, bundle: dict) -> list:
    """
    Genera las top 3 razones por las que el modelo favorece al ganador.
    Usa los coeficientes de LogReg para calcular la contribución de cada feature.
    Retorna lista de dicts: [{"reason": str, "impact": float}, ...]
    """
    try:
        winner_model = bundle["winner_model"]
        feature_names = bundle["feature_names"]

        if not hasattr(winner_model, "calibrated_classifiers_"):
            return []

        # Promedio de coeficientes de los 5 folds calibrados
        coefs = []
        for cc in winner_model.calibrated_classifiers_:
            est = cc.estimator
            if hasattr(est, "named_steps"):
                lr = est.named_steps.get("lr") or est.named_steps.get("model")
                scaler = est.named_steps.get("scaler")
                if lr and hasattr(lr, "coef_") and scaler and hasattr(scaler, "scale_"):
                    raw_coef = lr.coef_[0] / scaler.scale_
                    coefs.append(raw_coef)
            elif hasattr(est, "coef_"):
                coefs.append(est.coef_[0])

        if not coefs:
            return []

        avg_coef = np.mean(coefs, axis=0)
        x_vals = X[0]

        # Contribución = coeficiente × valor
        contributions = []
        for i, (feat, coef, val) in enumerate(zip(feature_names, avg_coef, x_vals)):
            contrib = coef * val
            contributions.append((feat, contrib, val))

        # Si B gana, invertimos el signo (contribuciones positivas favorecen A)
        winner_is_a = (winner_name == name_a)
        if not winner_is_a:
            contributions = [(f, -c, v) for f, c, v in contributions]

        # Filtrar: solo contribuciones positivas (que favorecen al ganador)
        positive = [(f, c, v) for f, c, v in contributions if c > 0]
        positive.sort(key=lambda x: x[1], reverse=True)

        # Generar razones legibles
        reasons = []
        seen_concepts = set()

        for feat, contrib, val in positive:
            if len(reasons) >= 3:
                break

            # Evitar razones duplicadas del mismo concepto
            concept = feat.replace("diff_", "").replace("a_", "").replace("b_", "")
            concept = concept.replace("recent_", "").replace("career_", "")
            if concept in seen_concepts:
                continue
            seen_concepts.add(concept)

            # Traducir a lenguaje humano
            human_name = FEATURE_TRANSLATIONS.get(feat, feat.replace("_", " ").replace("diff ", ""))

            # Construir razón con contexto
            if feat.startswith("diff_"):
                if "age" in feat:
                    age_diff = abs(val)
                    if val < 0:
                        reason = f"{int(age_diff)} anos mas joven"
                    else:
                        reason = f"Ventaja de experiencia por edad"
                elif val > 0:
                    reason = f"Mejor {human_name.lower()}"
                else:
                    reason = f"Mejor {human_name.lower()}"
            elif feat.startswith("a_") or feat.startswith("b_"):
                prefix = feat[:2]
                is_winner_stat = (prefix == "a_" and winner_is_a) or (prefix == "b_" and not winner_is_a)
                if is_winner_stat:
                    reason = f"{human_name}: {val:.2f}" if val < 10 else f"{human_name}: {val:.0f}"
                else:
                    reason = f"Oponente debil en {human_name.lower()}"
            else:
                reason = human_name

            reasons.append({
                "reason": reason,
                "feature": feat,
                "impact": round(float(contrib), 4),
            })

        return reasons

    except Exception:
        return []
