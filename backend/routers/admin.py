from __future__ import annotations

import sys
import subprocess as sp
from pathlib import Path

from fastapi import APIRouter, Depends

from backend.auth import require_admin
from backend.database import get_db, load_models
from db.db_helpers import param, is_postgresql

router = APIRouter(prefix="/admin")


@router.get("/dashboard")
async def admin_dashboard(user: dict = Depends(require_admin)):
    conn = get_db()

    db_stats = {}
    for table in ["fighters", "events", "fights", "fight_stats"]:
        db_stats[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    last_event = conn.execute("""
        SELECT name, date_parsed, location FROM events
        WHERE date_parsed IS NOT NULL
        ORDER BY date_parsed DESC LIMIT 1
    """).fetchone()

    total_fights_w_winner = conn.execute("""
        SELECT COUNT(*) FROM fights WHERE winner_name IS NOT NULL AND winner_name != ''
    """).fetchone()[0]

    recent_events = conn.execute("""
        SELECT e.name, e.date_parsed, e.location, COUNT(f.fight_id) as total_fights
        FROM events e
        LEFT JOIN fights f ON e.event_id = f.event_id
        WHERE e.date_parsed IS NOT NULL
        GROUP BY e.event_id
        ORDER BY e.date_parsed DESC
        LIMIT 5
    """).fetchall()

    top_active = conn.execute("""
        SELECT f.name, f.wins, f.losses, f.draws, f.weight_lbs, f.stance
        FROM fighters f
        WHERE f.wins + f.losses >= 5
        ORDER BY f.wins DESC
        LIMIT 10
    """).fetchall()

    methods = conn.execute("""
        SELECT
            CASE
                WHEN UPPER(method) LIKE '%KO%' OR UPPER(method) LIKE '%TKO%' THEN 'KO/TKO'
                WHEN UPPER(method) LIKE '%SUB%' THEN 'Submission'
                WHEN UPPER(method) LIKE '%DEC%' THEN 'Decision'
                ELSE 'Other'
            END as method_group,
            COUNT(*) as count
        FROM fights
        WHERE winner_name IS NOT NULL AND winner_name != ''
        GROUP BY method_group
        ORDER BY count DESC
    """).fetchall()

    bundle = load_models()
    model_info = {
        "features": len(bundle.get("feature_names", [])),
        "models": list(bundle.get("models", {}).keys()) if isinstance(bundle.get("models"), dict) else ["winner", "method", "distance", "round"],
    }

    if is_postgresql():
        fights_by_year_query = """
            SELECT SUBSTRING(e.date_parsed, 1, 4) as year, COUNT(f.fight_id) as count
            FROM fights f
            JOIN events e ON f.event_id = e.event_id
            WHERE e.date_parsed IS NOT NULL
            GROUP BY year
            ORDER BY year DESC
            LIMIT 10
        """
    else:
        fights_by_year_query = """
            SELECT SUBSTR(e.date_parsed, 1, 4) as year, COUNT(f.fight_id) as count
            FROM fights f
            JOIN events e ON f.event_id = e.event_id
            WHERE e.date_parsed IS NOT NULL
            GROUP BY year
            ORDER BY year DESC
            LIMIT 10
        """
    fights_by_year = conn.execute(fights_by_year_query).fetchall()

    conn.close()

    return {
        "database": db_stats,
        "last_event": dict(last_event) if last_event else None,
        "recent_events": [dict(e) for e in recent_events],
        "top_active_fighters": [dict(f) for f in top_active],
        "method_distribution": [dict(m) for m in methods],
        "model_info": model_info,
        "fights_by_year": [dict(f) for f in fights_by_year],
        "total_fights_with_result": total_fights_w_winner,
    }


@router.post("/update")
async def trigger_update(user: dict = Depends(require_admin)):
    conn = get_db()
    p = param()
    conn.execute(
        f"INSERT INTO update_logs (action, status) VALUES ({p}, {p})",
        ("upcoming", "running"),
    )
    conn.commit()

    if is_postgresql():
        log_id = conn.execute("SELECT LASTVAL()").fetchone()[0]
    else:
        log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    try:
        result = sp.run(
            [sys.executable, "scripts/scraping/scrape_upcoming.py"],
            capture_output=True, text=True, timeout=120,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        status = "success" if result.returncode == 0 else "error"
        output = (result.stdout or "") + (result.stderr or "")
        if len(output) > 2000:
            output = output[:2000] + "... (truncated)"
    except sp.TimeoutExpired:
        status = "error"
        output = "Timeout: scraper took more than 2 minutes"
    except Exception as e:
        status = "error"
        output = str(e)

    conn = get_db()
    conn.execute(
        f"UPDATE update_logs SET status = {p}, result = {p}, finished_at = CURRENT_TIMESTAMP WHERE id = {p}",
        (status, output, log_id),
    )
    conn.commit()
    conn.close()

    return {"status": status, "log_id": log_id, "output": output[:500]}


@router.get("/update-logs")
async def get_update_logs(user: dict = Depends(require_admin)):
    conn = get_db()
    logs = conn.execute("""
        SELECT id, action, status, result, started_at, finished_at
        FROM update_logs
        ORDER BY started_at DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    return {"logs": [dict(l) for l in logs]}


@router.get("/picks-stats")
async def admin_picks_stats(user: dict = Depends(require_admin)):
    conn = get_db()

    total_picks = conn.execute("SELECT COUNT(*) FROM picks").fetchone()[0]
    total_voters = conn.execute("SELECT COUNT(DISTINCT user_id) FROM picks").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'user'").fetchone()[0]

    by_event = conn.execute("""
        SELECT event_name, COUNT(*) as picks, COUNT(DISTINCT user_id) as voters
        FROM picks
        GROUP BY event_name
        ORDER BY event_name DESC
    """).fetchall()

    top_fights = conn.execute("""
        SELECT event_name, fighter_a, fighter_b,
               COUNT(*) as total_picks,
               SUM(CASE WHEN picked_winner = fighter_a THEN 1 ELSE 0 END) as picks_a,
               SUM(CASE WHEN picked_winner = fighter_b THEN 1 ELSE 0 END) as picks_b
        FROM picks
        GROUP BY event_name, fighter_a, fighter_b
        ORDER BY total_picks DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "total_picks": total_picks,
        "total_voters": total_voters,
        "total_users": total_users,
        "by_event": [dict(r) for r in by_event],
        "top_fights": [dict(r) for r in top_fights],
    }
