"""AppPulse - アプリ使用頻度追跡・管理ツール

Usage:
    python main.py              # トレイアイコン + バックグラウンドトラッキング
    python main.py --dashboard  # ダッシュボードGUIを直接起動
    python main.py --scan       # アプリ一覧をスキャンして表示
    python main.py --poll       # 1回だけプロセスポーリングを実行
"""
import argparse
import logging
import os
import sys
import threading
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    APP_NAME, APPDATA_DIR, DEVICE_ID, SYNC_INTERVAL_SECONDS,
    NOTIFICATION_INTERVAL_DAYS,
)
from storage.database import init_db
from tracker.process_monitor import ProcessMonitor

LOG_FILE = os.path.join(APPDATA_DIR, "apppulse.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def start_sync_loop():
    """Periodically export stats to sync folder."""
    from storage.sync import export_stats
    while True:
        time.sleep(SYNC_INTERVAL_SECONDS)
        try:
            export_stats()
        except Exception:
            logger.exception("Sync export failed")


def start_recommendation_loop():
    """Periodically show recommendations for top/bottom apps."""
    from tracker.usage_aggregator import get_top_apps, get_bottom_apps, format_duration
    from recommender.alternatives import get_alternatives
    from ui.notifications import show_recommendation, show_usage_summary

    interval = NOTIFICATION_INTERVAL_DAYS * 86400

    while True:
        time.sleep(interval)
        try:
            top = get_top_apps(n=1, days=30)
            bottom = get_bottom_apps(n=1, days=30)

            if top and bottom:
                show_usage_summary(
                    top[0]["process_name"],
                    bottom[0]["process_name"],
                    format_duration(top[0]["total_foreground_seconds"]),
                    format_duration(bottom[0]["total_foreground_seconds"]),
                )

            # Show recommendation for the most used app
            if top:
                alts = get_alternatives(top[0]["process_name"])
                if alts:
                    alt = alts[0]
                    show_recommendation(
                        top[0]["process_name"],
                        alt["name"],
                        alt["reason"],
                        alt.get("winget_id"),
                    )
        except Exception:
            logger.exception("Recommendation loop error")


def run_tray():
    """Run the app with system tray icon."""
    from ui.tray_icon import TrayIcon

    monitor = ProcessMonitor()
    monitor.start()

    def open_dashboard():
        from ui.dashboard import Dashboard
        threading.Thread(target=lambda: Dashboard().run(), daemon=True).start()

    def on_quit():
        monitor.stop()
        logger.info("AppPulse shutting down")
        os._exit(0)

    def on_pause_resume(paused):
        if paused:
            monitor.stop()
            logger.info("Tracking paused")
        else:
            monitor.start()
            logger.info("Tracking resumed")

    tray = TrayIcon(
        on_open_dashboard=open_dashboard,
        on_quit=on_quit,
        on_pause_resume=on_pause_resume,
    )

    # Start background threads
    threading.Thread(target=start_sync_loop, daemon=True).start()
    threading.Thread(target=start_recommendation_loop, daemon=True).start()

    logger.info("AppPulse started on %s", DEVICE_ID)
    tray.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        on_quit()


def run_dashboard():
    """Run dashboard directly."""
    from ui.dashboard import Dashboard
    Dashboard().run()


def run_scan():
    """Scan and print installed apps."""
    from manager.app_inventory import scan_installed_apps
    apps = scan_installed_apps()
    print(f"\n{len(apps)} 件のアプリを検出しました:\n")
    for app in sorted(apps, key=lambda a: a["app_name"]):
        wid = app.get("winget_id") or ""
        print(f"  {app['app_name']:<40} {wid}")


def run_poll():
    """Run a single process poll."""
    monitor = ProcessMonitor()
    monitor.poll_once_sync()
    print("ポーリング完了。使用状況がDBに記録されました。")


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--dashboard", action="store_true",
                        help="ダッシュボードGUIを直接起動")
    parser.add_argument("--scan", action="store_true",
                        help="アプリ一覧をスキャン")
    parser.add_argument("--poll", action="store_true",
                        help="1回だけプロセスポーリング")
    args = parser.parse_args()

    init_db()

    if args.dashboard:
        run_dashboard()
    elif args.scan:
        run_scan()
    elif args.poll:
        run_poll()
    else:
        run_tray()


if __name__ == "__main__":
    main()
