import logging
import os
import subprocess
import sys

from winotify import Notification, audio

from config import APP_NAME, APPDATA_DIR

logger = logging.getLogger(__name__)

ICON_PATH = os.path.join(APPDATA_DIR, "icon.ico")


def _get_icon():
    if os.path.exists(ICON_PATH):
        return ICON_PATH
    return ""


def show_recommendation(app_name, alternative_name, reason, winget_id=None):
    """Show a toast notification recommending an alternative app."""
    try:
        toast = Notification(
            app_id=APP_NAME,
            title=f"{app_name} の代替アプリ",
            msg=f"{alternative_name}: {reason}",
            duration="long",
            icon=_get_icon(),
        )
        if winget_id:
            toast.add_actions(
                label=f"{alternative_name} をインストール",
                launch=f"apppulse://install/{winget_id}",
            )
        toast.add_actions(label="閉じる", launch="apppulse://dismiss")
        toast.show()
        logger.info("Recommendation shown: %s -> %s", app_name, alternative_name)
    except Exception:
        logger.exception("Failed to show recommendation notification")


def show_usage_summary(top_app, bottom_app, top_time, bottom_time):
    """Show a summary notification about app usage."""
    try:
        toast = Notification(
            app_id=APP_NAME,
            title="AppPulse 使用状況サマリー",
            msg=(
                f"最も使用: {top_app} ({top_time})\n"
                f"最も未使用: {bottom_app} ({bottom_time})"
            ),
            duration="long",
            icon=_get_icon(),
        )
        toast.add_actions(label="ダッシュボードを開く", launch="apppulse://dashboard")
        toast.show()
    except Exception:
        logger.exception("Failed to show usage summary notification")


def show_uninstall_success(app_name):
    """Show a notification that an app was successfully uninstalled."""
    try:
        toast = Notification(
            app_id=APP_NAME,
            title="アンインストール完了",
            msg=f"{app_name} を正常にアンインストールしました",
            icon=_get_icon(),
        )
        toast.show()
    except Exception:
        logger.exception("Failed to show uninstall notification")
