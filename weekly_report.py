"""AppPulse 週次レポート - 毎週土曜に自動実行されるスクリプト

実行内容:
1. インストール済みアプリをスキャン
2. 使用頻度ランキングを計算
3. 最上位/最下位アプリを特定
4. 代替アプリのレコメンド通知を表示
5. 週次レポートをMarkdownファイルで出力
6. マルチデバイス同期データをエクスポート
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from config import APP_NAME, APPDATA_DIR, DEVICE_ID

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


def run_weekly():
    from storage.database import init_db
    from manager.app_inventory import scan_installed_apps
    from tracker.process_monitor import ProcessMonitor
    from tracker.usage_aggregator import (
        get_top_apps, get_bottom_apps, format_duration,
    )
    from recommender.alternatives import get_alternatives
    from ui.notifications import show_recommendation, show_usage_summary
    from storage.sync import export_stats

    init_db()
    logger.info("=== Weekly report started on %s ===", DEVICE_ID)

    # 1. Process poll
    monitor = ProcessMonitor()
    monitor.poll_once_sync()
    logger.info("Process poll completed")

    # 2. Scan installed apps
    apps = scan_installed_apps()
    logger.info("Scanned %d apps", len(apps))

    # 3. Get rankings
    top = get_top_apps(n=10, days=7)
    bottom = get_bottom_apps(n=10, days=7)

    # 4. Show notification
    if top and bottom:
        top_time = format_duration(top[0]["total_foreground_seconds"])
        bot_time = format_duration(bottom[0]["total_foreground_seconds"])
        show_usage_summary(
            top[0]["process_name"], bottom[0]["process_name"],
            top_time, bot_time,
        )

    # 5. Show recommendations for top used app
    if top:
        alts = get_alternatives(top[0]["process_name"])
        if alts:
            show_recommendation(
                top[0]["process_name"],
                alts[0]["name"],
                alts[0]["reason"],
                alts[0].get("winget_id"),
            )

    # 6. Generate markdown report
    report = _generate_report(top, bottom, apps)
    report_dir = os.path.join(APPDATA_DIR, "reports")
    os.makedirs(report_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(report_dir, f"weekly_{date_str}_{DEVICE_ID}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Report saved to %s", report_path)

    # 7. Sync
    try:
        export_stats()
        logger.info("Sync export completed")
    except Exception:
        logger.exception("Sync export failed")

    logger.info("=== Weekly report completed ===")
    return report_path


def _generate_report(top, bottom, installed_apps):
    from tracker.usage_aggregator import format_duration
    from recommender.alternatives import get_alternatives
    from storage.database import get_all_rejections

    now = datetime.now()
    lines = [
        f"# AppPulse 週次レポート",
        f"",
        f"- 生成日時: {now.strftime('%Y-%m-%d %H:%M')}",
        f"- デバイス: {DEVICE_ID}",
        f"- インストール済みアプリ数: {len(installed_apps)}",
        f"",
        f"## 最も使用しているアプリ (Top 10)",
        f"",
        f"| # | アプリ名 | フォアグラウンド時間 | 検出回数 | スコア |",
        f"|---|---------|-------------------|---------|-------|",
    ]
    for app in top:
        lines.append(
            f"| {app['rank']} | {app['process_name']} | "
            f"{format_duration(app['total_foreground_seconds'])} | "
            f"{app['total_launches']} | {app['score']} |"
        )

    lines.extend([
        f"",
        f"## 最も使用していないアプリ (Bottom 10)",
        f"",
        f"| # | アプリ名 | フォアグラウンド時間 | スコア | 代替候補 |",
        f"|---|---------|-------------------|-------|---------|",
    ])
    for app in bottom:
        alts = get_alternatives(app["process_name"])
        alt_text = alts[0]["name"] if alts else "-"
        lines.append(
            f"| {app['rank']} | {app['process_name']} | "
            f"{format_duration(app['total_foreground_seconds'])} | "
            f"{app['score']} | {alt_text} |"
        )

    # Rejection history
    rejections = get_all_rejections(DEVICE_ID)
    if rejections:
        lines.extend([
            f"",
            f"## 削除見送り履歴",
            f"",
            f"| アプリ名 | 見送り回数 | 最終見送り日 |",
            f"|---------|----------|-----------|",
        ])
        for r in rejections:
            lines.append(
                f"| {r['app_name']} | {r['rejection_count']}回 | "
                f"{r['last_rejected'][:10]} |"
            )

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    run_weekly()
