import json
import logging
import os
from datetime import datetime
from glob import glob

from config import DEVICE_ID, SYNC_DIR
from storage.database import get_all_usage_stats

logger = logging.getLogger(__name__)


def export_stats():
    """Export current device's usage stats to the sync folder."""
    os.makedirs(SYNC_DIR, exist_ok=True)
    stats = get_all_usage_stats(device_id=DEVICE_ID)
    data = {
        "device_id": DEVICE_ID,
        "exported_at": datetime.now().isoformat(),
        "stats": [dict(row) for row in stats],
    }
    path = os.path.join(SYNC_DIR, f"{DEVICE_ID}_usage_stats.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Exported stats to %s", path)
    return path


def import_all_stats():
    """Import usage stats from all devices in the sync folder.

    Returns dict: {device_id: [stats_list]}
    """
    if not os.path.isdir(SYNC_DIR):
        return {}

    all_stats = {}
    for path in glob(os.path.join(SYNC_DIR, "*_usage_stats.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            dev = data.get("device_id", "unknown")
            all_stats[dev] = data.get("stats", [])
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to import %s", path)
    return all_stats


def get_sync_status():
    """Check sync folder status."""
    if not os.path.isdir(SYNC_DIR):
        return {"available": False, "devices": []}

    devices = []
    for path in glob(os.path.join(SYNC_DIR, "*_usage_stats.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            devices.append({
                "device_id": data.get("device_id", "unknown"),
                "exported_at": data.get("exported_at", ""),
                "app_count": len(data.get("stats", [])),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return {"available": True, "devices": devices}
