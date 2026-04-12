"""
Router de picks y leaderboard.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends

from backend.auth import get_current_user
from backend.database import get_db, load_models, load_fighter_cache
from backend.schemas import PickRequest
from backend.services.predictions import compute_live_features

router = APIRouter()


@router.post("/picks")
async def submit_pick(pick: PickRequest, user: dict = Depends(get_current_user)):
    """Enviar o actualizar un pick para una pelea."""
    if pick.picked_winner not in [pick.fighter_a, pick.fighter_b]:
        raise HTTPException(status_code=400, detail="El pick debe ser uno de los dos peleadores")

    conn = get_db()
    db_user = conn.execute("SELECT id FROM users WHERE username = ?", (user["sub"],)).fetchone()
    if not db_user:
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_id = db_user["id"]

    # Upsert: si ya existe el pick para esta pelea, actualizarlo
    existing = conn.execute(
        "SELECT id FROM picks WHERE user_id = ? AND event_name = ? AND fighter_a = ? AND fighter_b = ?",
        (user_id, pick.event_name, pick.fighter_a, pick.fighter_b),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE picks SET picked_winner = ?, created_at = CURRENT_TIMESTAMP WHERE id = ?",
            (pick.picked_winner, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO picks (user_id, event_name, fighter_a, fighter_b, picked_winner) VALUES (?, ?, ?, ?, ?)",
            (user_id, pick.event_name, pick.fighter_a, pick.fighter_b, pick.picked_winner),
        )

    conn.commit()
    conn.close()
    return {"ok": True, "picked_winner": pick.picked_winner}


@router.get("/picks/{event_name}")
async def get_picks(event_name: str, user: dict = Depends(get_current_user)):
    """Obtener los picks del usuario para un evento."""
    conn = get_db()
    db_user = conn.execute("SELECT id FROM users WHERE username = ?", (user["sub"],)).fetchone()
    if not db_user:
        conn.close()
        return {"picks": []}

    picks = conn.execute(
        "SELECT fighter_a, fighter_b, picked_winner FROM picks WHERE user_id = ? AND event_name = ?",
        (db_user["id"], event_name),
    ).fetchall()
    conn.close()
    return {"picks": [dict(p) for p in picks]}


@router.get("/leaderboard")
async def get_leaderboard():
    """
    Leaderboard: compara accuracy de usuarios vs CageMind.
    Solo cuenta peleas que ya tienen resultado (winner_name en fights).
    """
    conn = get_db()

    # Obtener todos los picks con resultado real
    rows = conn.execute("""
        SELECT
            u.username,
            p.event_name,
            p.fighter_a,
            p.fighter_b,
            p.picked_winner,
            f.winner_name
        FROM picks p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN fights f ON (
            (f.fighter_a_name = p.fighter_a AND f.fighter_b_name = p.fighter_b)
            OR (f.fighter_a_name = p.fighter_b AND f.fighter_b_name = p.fighter_a)
        )
        WHERE f.winner_name IS NOT NULL AND f.winner_name != ''
    """).fetchall()

    # Calcular stats por usuario
    user_stats: dict = {}
    for row in rows:
        username = row["username"]
        if username not in user_stats:
            user_stats[username] = {"correct": 0, "total": 0}
        user_stats[username]["total"] += 1
        if row["picked_winner"] == row["winner_name"]:
            user_stats[username]["correct"] += 1

    # Calcular accuracy de CageMind (modelo) en las mismas peleas
    model_correct = 0
    model_total = 0
    fighters = load_fighter_cache()
    bundle = load_models()

    seen_fights: set = set()
    for row in rows:
        fight_key = f"{row['fighter_a']}|{row['fighter_b']}"
        if fight_key in seen_fights:
            continue
        seen_fights.add(fight_key)

        try:
            features = compute_live_features(row["fighter_a"], row["fighter_b"])
            winner_model = bundle["models"]["winner"]
            proba = winner_model.predict_proba(features)[0]
            predicted = row["fighter_a"] if proba[1] > 0.5 else row["fighter_b"]
            model_total += 1
            if predicted == row["winner_name"]:
                model_correct += 1
        except Exception:
            pass

    conn.close()

    # Build leaderboard
    leaderboard = []
    for username, stats in user_stats.items():
        pct = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
        leaderboard.append({
            "username": username,
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": pct,
        })

    leaderboard.sort(key=lambda x: (-x["accuracy"], -x["total"]))

    model_accuracy = round(model_correct / model_total * 100, 1) if model_total > 0 else 0

    return {
        "leaderboard": leaderboard,
        "cagemind": {
            "correct": model_correct,
            "total": model_total,
            "accuracy": model_accuracy,
        },
    }
