"""
Router de odds y value bets.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.config import VALUE_THRESHOLD
from backend.database import load_models, load_fighter_cache
from backend.services.predictions import (
    calibrate_proba, compute_live_features, assess_data_quality, apply_newcomer_adjustment,
)
from backend.services.odds import fetch_odds, american_to_prob, match_fighter_names

router = APIRouter()


@router.get("/odds")
async def get_odds():
    """Retorna odds actuales de casas de apuestas para peleas UFC próximas."""
    odds_data = fetch_odds()
    if not odds_data:
        return {"odds": [], "source": "the-odds-api", "error": "No odds available or API key not configured"}
    return {"odds": odds_data, "source": "the-odds-api", "count": len(odds_data)}


@router.get("/value-bets")
async def get_value_bets():
    """
    Compara predicciones de CageMind con odds de casas de apuestas.
    Retorna peleas donde CageMind ve una ventaja > 10% sobre las odds implícitas.
    """
    odds_data = fetch_odds()
    if not odds_data:
        return {
            "value_bets": [],
            "total_fights_analyzed": 0,
            "source": "the-odds-api",
            "error": "No odds available. Configure ODDS_API_KEY in environment variables."
        }

    fighters = load_fighter_cache()
    bundle = load_models()
    value_bets = []
    fights_analyzed = 0

    for event in odds_data:
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        commence = event.get("commence_time", "")

        # Matchear nombres con BD
        name_a = match_fighter_names(home, fighters)
        name_b = match_fighter_names(away, fighters)

        if not name_a or not name_b:
            continue

        # Obtener predicción CageMind
        try:
            X = compute_live_features(name_a, name_b)
            quality = assess_data_quality(name_a, name_b)

            winner_proba = bundle["winner_model"].predict_proba(X)[0]
            raw_a = float(winner_proba[1])
            raw_b = float(winner_proba[0])
            prob_a, prob_b = calibrate_proba(raw_a, raw_b)
            prob_a, prob_b = apply_newcomer_adjustment(prob_a, prob_b, quality)
        except Exception:
            continue

        fights_analyzed += 1

        # Promediar odds de todas las casas
        for bookmaker in event.get("bookmakers", []):
            book_name = bookmaker.get("title", "Unknown")
            markets = bookmaker.get("markets", [])

            for market in markets:
                if market.get("key") != "h2h":
                    continue

                outcomes = market.get("outcomes", [])
                if len(outcomes) < 2:
                    continue

                # Matchear outcomes con fighters
                for outcome in outcomes:
                    out_name = outcome.get("name", "")
                    out_price = outcome.get("price", 0)

                    matched = match_fighter_names(out_name, fighters)
                    if not matched or out_price == 0:
                        continue

                    implied_prob = american_to_prob(out_price)
                    cagemind_prob = prob_a if matched == name_a else prob_b

                    # Calcular value
                    value = (cagemind_prob / implied_prob) - 1

                    if value > VALUE_THRESHOLD and quality["confidence"] == "HIGH":
                        value_bets.append({
                            "fighter": matched,
                            "opponent": name_b if matched == name_a else name_a,
                            "bookmaker": book_name,
                            "american_odds": out_price,
                            "implied_prob": round(implied_prob, 4),
                            "cagemind_prob": round(cagemind_prob, 4),
                            "value_pct": round(value * 100, 1),
                            "confidence": quality["confidence"],
                            "commence_time": commence,
                        })

    # Deduplicate: keep best value per fighter across bookmakers
    best_bets = {}
    for bet in value_bets:
        key = bet["fighter"]
        if key not in best_bets or bet["value_pct"] > best_bets[key]["value_pct"]:
            best_bets[key] = bet

    final_bets = sorted(best_bets.values(), key=lambda x: x["value_pct"], reverse=True)

    return {
        "value_bets": final_bets,
        "total_fights_analyzed": fights_analyzed,
        "total_value_bets": len(final_bets),
        "threshold": f"{VALUE_THRESHOLD*100:.0f}%",
        "source": "the-odds-api",
    }
