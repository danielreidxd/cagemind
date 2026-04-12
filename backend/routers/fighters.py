"""
Router de peleadores: búsqueda y perfil detallado.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.database import get_db, load_fighter_cache, load_fighter_stats_cache

router = APIRouter()


@router.get("/fighters")
async def list_fighters(
    search: str = Query(default="", description="Buscar por nombre"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    min_fights: int = Query(default=0, ge=0, description="Minimo de peleas"),
):
    """Lista peleadores con búsqueda opcional."""
    conn = get_db()

    query = "SELECT name, wins, losses, draws, weight_lbs, stance, height_inches, reach_inches FROM fighters"
    params = []
    conditions = []

    if search:
        conditions.append("LOWER(name) LIKE ?")
        params.append("%" + search.lower() + "%")

    if min_fights > 0:
        conditions.append("(wins + losses + draws) >= ?")
        params.append(min_fights)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY (wins + losses + draws) DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "count": len(rows),
        "fighters": [dict(r) for r in rows]
    }


@router.get("/fighters/{name}")
async def get_fighter(name: str):
    """Perfil detallado de un peleador."""
    fighters = load_fighter_cache()
    stats = load_fighter_stats_cache()

    # Buscar por nombre exacto o parcial
    info = fighters.get(name)
    if not info:
        # Buscar parcial
        matches = [n for n in fighters if name.lower() in n.lower()]
        if len(matches) == 1:
            info = fighters[matches[0]]
            name = matches[0]
        elif len(matches) > 1:
            return {"error": "Múltiples coincidencias", "matches": matches[:10]}
        else:
            raise HTTPException(status_code=404, detail="Peleador no encontrado")

    fighter_stats = stats.get(name, {})

    conn = get_db()
    # Últimas 5 peleas
    recent_fights = conn.execute("""
        SELECT f.fighter_a_name, f.fighter_b_name, f.winner_name,
               f.method, f.round, f.weight_class, e.date_parsed
        FROM fights f
        JOIN events e ON f.event_id = e.event_id
        WHERE f.fighter_a_name = ? OR f.fighter_b_name = ?
        ORDER BY e.date_parsed DESC
        LIMIT 5
    """, (name, name)).fetchall()
    conn.close()

    recent = []
    for r in recent_fights:
        opponent = r["fighter_b_name"] if r["fighter_a_name"] == name else r["fighter_a_name"]
        won = r["winner_name"] == name
        recent.append({
            "opponent": opponent,
            "result": "W" if won else ("L" if r["winner_name"] else "NC/Draw"),
            "method": r["method"],
            "round": r["round"],
            "date": r["date_parsed"],
        })

    return {
        "profile": info,
        "career_stats": fighter_stats,
        "recent_fights": recent,
    }
