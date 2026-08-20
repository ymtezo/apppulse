import json
import logging
import os

logger = logging.getLogger(__name__)

_ALTERNATIVES_FILE = os.path.join(os.path.dirname(__file__), "alternatives.json")
_cache = None


def _load():
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_ALTERNATIVES_FILE, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.exception("Failed to load alternatives.json")
        _cache = {}
    return _cache


def get_alternatives(app_name):
    """Get alternative apps for a given app name.

    Returns list of dicts: [{name, winget_id, reason}, ...]
    """
    db = _load()

    # Exact match
    if app_name in db:
        return db[app_name].get("alternatives", [])

    # Partial match (case-insensitive)
    name_lower = app_name.lower()
    for key, val in db.items():
        if name_lower in key.lower() or key.lower() in name_lower:
            return val.get("alternatives", [])

    return []


def get_category(app_name):
    """Get the category of an app."""
    db = _load()
    if app_name in db:
        return db[app_name].get("category", "unknown")
    name_lower = app_name.lower()
    for key, val in db.items():
        if name_lower in key.lower() or key.lower() in name_lower:
            return val.get("category", "unknown")
    return "unknown"


def find_installed_alternative(app_name, installed_app_names):
    """Check if user already has an alternative installed.

    Returns the name of the installed alternative, or None.
    """
    alternatives = get_alternatives(app_name)
    installed_lower = {n.lower() for n in installed_app_names}

    for alt in alternatives:
        if alt["name"].lower() in installed_lower:
            return alt["name"]
    return None
