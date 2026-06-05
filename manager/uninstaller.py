import logging

from config import DEVICE_ID, UNINSTALL_BLOCKLIST
from storage.database import (
    insert_deletion_log,
    remove_installed_app,
)
from utils.winget_wrapper import uninstall_app

logger = logging.getLogger(__name__)


def is_blocked(winget_id=None, app_name=None):
    """Check if an app is on the uninstall blocklist."""
    if winget_id:
        for blocked in UNINSTALL_BLOCKLIST:
            if blocked.lower() in winget_id.lower():
                return True
    if app_name:
        blocked_names = {
            "windows", "explorer", "edge", "terminal", "powershell",
            "desktop app installer", ".net", "visual c++",
        }
        name_lower = app_name.lower()
        for blocked in blocked_names:
            if blocked in name_lower:
                return True
    return False


def uninstall(app_name, winget_id=None, exe_path=None, reason="manual",
              usage_rank=None, total_foreground_seconds=None,
              confirmed=False):
    """Uninstall an app and log the result.

    confirmed must be explicitly set to True by the caller.
    This prevents accidental uninstallation from any code path.

    Returns (success: bool, message: str).
    """
    if not confirmed:
        msg = (f"アンインストール未確認: {app_name}\n"
               "uninstall() の呼び出し時に confirmed=True を指定してください。")
        logger.warning(msg)
        return False, msg

    if is_blocked(winget_id, app_name):
        msg = f"ブロックリストに含まれるためアンインストールできません: {app_name}"
        logger.warning(msg)
        return False, msg

    # Attempt uninstall via winget
    method = None
    success = False
    output = ""

    if winget_id:
        method = "winget_id"
        success, output = uninstall_app(app_id=winget_id)

    if not success:
        method = "winget_name"
        success, output = uninstall_app(app_name=app_name)

    # Log the result
    insert_deletion_log(
        app_name=app_name,
        device_id=DEVICE_ID,
        reason=reason,
        winget_id=winget_id,
        exe_path=exe_path,
        usage_rank=usage_rank,
        total_foreground_seconds=total_foreground_seconds,
        uninstall_method=method,
        success=success,
    )

    if success:
        remove_installed_app(app_name, DEVICE_ID)
        msg = f"アンインストール成功: {app_name}"
        logger.info(msg)
    else:
        msg = f"アンインストール失敗: {app_name}\n{output}"
        logger.error(msg)

    return success, msg
