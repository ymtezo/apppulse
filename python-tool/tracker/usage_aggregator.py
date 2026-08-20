from datetime import datetime, timedelta

from config import (
    DEVICE_ID,
    WEIGHT_FOREGROUND_TIME,
    WEIGHT_LAUNCHES,
    WEIGHT_RECENCY,
)
from storage.database import get_db


def _normalize(values):
    """Min-max normalize a list of numbers to [0, 1]."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def get_rankings(device_id=None, days=30):
    """Return apps ranked by combined usage score.

    Returns list of dicts:
        process_name, total_foreground_seconds, total_launches,
        last_used, score
    """
    dev = device_id or DEVICE_ID
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                process_name,
                COUNT(*) AS total_events,
                SUM(CASE WHEN is_foreground = 1 THEN duration_seconds ELSE 0 END)
                    AS fg_seconds,
                MAX(timestamp) AS last_used,
                MIN(timestamp) AS first_seen
            FROM usage_events
            WHERE device_id = ? AND timestamp >= ?
            GROUP BY process_name
            ORDER BY fg_seconds DESC
            """,
            (dev, cutoff),
        ).fetchall()

    if not rows:
        return []

    now = datetime.now()
    fg_vals = [r["fg_seconds"] or 0 for r in rows]
    launch_vals = [r["total_events"] for r in rows]
    recency_vals = []
    for r in rows:
        last = datetime.fromisoformat(r["last_used"])
        days_ago = max((now - last).total_seconds() / 86400, 0)
        recency_vals.append(max(0, 1.0 - days_ago / max(days, 1)))

    norm_fg = _normalize(fg_vals)
    norm_launch = _normalize(launch_vals)

    results = []
    for i, r in enumerate(rows):
        score = (
            WEIGHT_FOREGROUND_TIME * norm_fg[i]
            + WEIGHT_LAUNCHES * norm_launch[i]
            + WEIGHT_RECENCY * recency_vals[i]
        )
        results.append({
            "process_name": r["process_name"],
            "total_foreground_seconds": fg_vals[i],
            "total_launches": launch_vals[i],
            "last_used": r["last_used"],
            "first_seen": r["first_seen"],
            "score": round(score, 4),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    for rank, item in enumerate(results, 1):
        item["rank"] = rank

    return results


def get_top_apps(n=10, device_id=None, days=30):
    return get_rankings(device_id, days)[:n]


def get_bottom_apps(n=10, device_id=None, days=30):
    rankings = get_rankings(device_id, days)
    return rankings[-n:] if rankings else []


def get_unused_apps(installed_apps, device_id=None, days=30):
    """Find installed apps that never appear in usage events.

    Args:
        installed_apps: list of app dicts with 'app_name' key
    """
    rankings = get_rankings(device_id, days)
    tracked_names = {r["process_name"].lower() for r in rankings}

    unused = []
    for app in installed_apps:
        name = app["app_name"] if isinstance(app, dict) else app["app_name"]
        if name.lower() not in tracked_names:
            unused.append(dict(app))
    return unused


def format_duration(seconds):
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}秒"
    if seconds < 3600:
        return f"{seconds // 60}分"
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    if mins:
        return f"{hours}時間{mins}分"
    return f"{hours}時間"
