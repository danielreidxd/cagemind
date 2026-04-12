"""
Router de analytics: tracking y reportes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth import require_admin
from backend.database import get_db
from backend.schemas import TrackEvent

router = APIRouter()


@router.post("/analytics/track")
async def track_event(event: TrackEvent):
    """Registra un evento de analytics (público, no requiere auth)."""
    conn = get_db()
    conn.execute(
        "INSERT INTO analytics_events (event_type, page, detail) VALUES (?, ?, ?)",
        (event.event_type, event.page, event.detail),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/admin/analytics")
async def get_analytics(user: dict = Depends(require_admin)):
    """Estadísticas de uso del sistema."""
    conn = get_db()

    # Total de eventos
    total_events = conn.execute("SELECT COUNT(*) FROM analytics_events").fetchone()[0]

    # Eventos por tipo
    by_type = conn.execute("""
        SELECT event_type, COUNT(*) as count
        FROM analytics_events
        GROUP BY event_type
        ORDER BY count DESC
    """).fetchall()

    # Page views por sección
    by_page = conn.execute("""
        SELECT page, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'page_view' AND page IS NOT NULL
        GROUP BY page
        ORDER BY count DESC
    """).fetchall()

    # Predicciones por día (últimos 14 días)
    predictions_daily = conn.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'prediction'
        GROUP BY day
        ORDER BY day DESC
        LIMIT 14
    """).fetchall()

    # Peleadores más buscados
    top_searched = conn.execute("""
        SELECT detail, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'search' AND detail IS NOT NULL AND detail != ''
        GROUP BY detail
        ORDER BY count DESC
        LIMIT 15
    """).fetchall()

    # Predicciones más populares (pares de peleadores)
    top_predictions = conn.execute("""
        SELECT detail, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'prediction' AND detail IS NOT NULL
        GROUP BY detail
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    # Actividad por hora (distribución)
    by_hour = conn.execute("""
        SELECT CAST(STRFTIME('%H', created_at) AS INTEGER) as hour, COUNT(*) as count
        FROM analytics_events
        GROUP BY hour
        ORDER BY hour
    """).fetchall()

    conn.close()

    return {
        "total_events": total_events,
        "by_type": [dict(r) for r in by_type],
        "by_page": [dict(r) for r in by_page],
        "predictions_daily": [dict(r) for r in predictions_daily],
        "top_searched": [dict(r) for r in top_searched],
        "top_predictions": [dict(r) for r in top_predictions],
        "by_hour": [dict(r) for r in by_hour],
    }
