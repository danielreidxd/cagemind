"""
Router de estadísticas generales.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.database import get_db, load_models

router = APIRouter()


@router.get("/stats")
async def get_stats():
    """Estadísticas generales de la base de datos."""
    conn = get_db()

    stats = {}
    for table in ["fighters", "events", "fights", "fight_stats"]:
        count = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        stats[table] = count

    # Último evento
    last_event = conn.execute("""
        SELECT name, date_parsed FROM events
        WHERE date_parsed IS NOT NULL
        ORDER BY date_parsed DESC LIMIT 1
    """).fetchone()

    # Top peleadores por victorias
    top_fighters = conn.execute("""
        SELECT name, wins, losses, draws FROM fighters
        ORDER BY wins DESC LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "database": stats,
        "last_event": dict(last_event) if last_event else None,
        "top_fighters_by_wins": [dict(f) for f in top_fighters],
        "model_info": {
            "features": len(load_models()["feature_names"]),
            "models": ["winner", "method", "distance", "round"],
        }
    }
