import logging
import subprocess

from config import DEVICE_ID
from storage.database import upsert_installed_app, get_installed_apps
from utils.winget_wrapper import list_installed

logger = logging.getLogger(__name__)


def _get_registry_apps():
    """Get installed apps from Windows registry via PowerShell."""
    ps_script = r"""
    $paths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($path in $paths) {
        Get-ItemProperty $path -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName } |
            Select-Object DisplayName, UninstallString, InstallDate,
                          InstallLocation, Publisher |
            ConvertTo-Json -Compress
    }
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return []

        import json
        apps = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, list):
                    apps.extend(data)
                elif isinstance(data, dict):
                    apps.append(data)
            except json.JSONDecodeError:
                continue
        return apps
    except Exception:
        logger.exception("Failed to read registry apps")
        return []


def scan_installed_apps():
    """Scan all installed apps from winget + registry and store in DB.

    Returns the merged list of app dicts.
    """
    apps = {}

    # Source 1: winget list
    for row in list_installed():
        name = row.get("Name") or row.get("名前") or ""
        if not name:
            continue
        winget_id = row.get("Id") or row.get("ID") or ""
        apps[name.lower()] = {
            "app_name": name,
            "winget_id": winget_id or None,
            "exe_path": None,
            "install_date": None,
        }

    # Source 2: registry
    for reg_app in _get_registry_apps():
        name = reg_app.get("DisplayName", "")
        if not name:
            continue
        key = name.lower()
        if key not in apps:
            apps[key] = {
                "app_name": name,
                "winget_id": None,
                "exe_path": reg_app.get("InstallLocation"),
                "install_date": reg_app.get("InstallDate"),
            }
        else:
            # Enrich existing entry with registry data
            if not apps[key]["exe_path"]:
                apps[key]["exe_path"] = reg_app.get("InstallLocation")
            if not apps[key]["install_date"]:
                apps[key]["install_date"] = reg_app.get("InstallDate")

    # Store in database
    for app in apps.values():
        upsert_installed_app(
            app_name=app["app_name"],
            device_id=DEVICE_ID,
            winget_id=app.get("winget_id"),
            exe_path=app.get("exe_path"),
            install_date=app.get("install_date"),
        )

    logger.info("Scanned %d installed apps on %s", len(apps), DEVICE_ID)
    return list(apps.values())


def get_all_apps(device_id=None):
    """Return all installed apps from DB."""
    return [dict(row) for row in get_installed_apps(device_id)]
