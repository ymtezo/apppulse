"""AppPulse Android Tracker (Termux版)

Termux上で動作するAndroid用の使用状況トラッカー。
Androidの `dumpsys usagestats` を使ってアプリ使用統計を取得する。

使い方:
    python android_tracker.py          # スキャン + レポート
    python android_tracker.py --poll   # 1回だけ使用統計を取得
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEVICE_ID, APPDATA_DIR
from storage.database import init_db, insert_usage_event, upsert_usage_stats


def get_android_usage_stats():
    """Get app usage stats via Android's dumpsys (requires Termux)."""
    try:
        result = subprocess.run(
            ["dumpsys", "usagestats"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            # Fallback: try with su or termux-usagestats
            return _get_stats_via_termux_api()
        return _parse_dumpsys(result.stdout)
    except FileNotFoundError:
        print("dumpsys が見つかりません。Termux環境で実行してください。")
        return []
    except Exception as e:
        print(f"エラー: {e}")
        return []


def _get_stats_via_termux_api():
    """Fallback: use termux-api to get battery/process info."""
    apps = []
    try:
        # Get running processes
        result = subprocess.run(
            ["ps", "-A", "-o", "comm"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines()[1:]:
                name = line.strip()
                if name and not name.startswith("["):
                    apps.append({
                        "package": name,
                        "foreground_seconds": 0,
                        "last_used": datetime.now().isoformat(),
                    })
    except Exception:
        pass
    return apps


def _parse_dumpsys(output):
    """Parse dumpsys usagestats output."""
    apps = []
    # Look for package usage entries
    pattern = re.compile(
        r'package=(\S+)\s+.*?totalTime[=:]"?(\d+)"?',
        re.IGNORECASE,
    )
    for match in pattern.finditer(output):
        pkg = match.group(1)
        total_ms = int(match.group(2))
        apps.append({
            "package": pkg,
            "foreground_seconds": total_ms // 1000,
            "last_used": datetime.now().isoformat(),
        })
    return apps


def get_installed_packages():
    """Get list of installed Android packages."""
    try:
        result = subprocess.run(
            ["pm", "list", "packages", "-3"],  # -3 = third-party only
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            packages = []
            for line in result.stdout.strip().splitlines():
                pkg = line.replace("package:", "").strip()
                if pkg:
                    packages.append(pkg)
            return packages
    except FileNotFoundError:
        pass
    return []


def poll_android():
    """Record current Android app usage to DB."""
    stats = get_android_usage_stats()
    if not stats:
        print("使用統計を取得できませんでした。")
        return

    for app in stats:
        insert_usage_event(
            process_name=app["package"],
            exe_path="",
            device_id=DEVICE_ID,
            is_foreground=False,
        )
        if app["foreground_seconds"] > 0:
            upsert_usage_stats(
                process_name=app["package"],
                device_id=DEVICE_ID,
                foreground_seconds=app["foreground_seconds"],
            )

    print(f"{len(stats)} 件のアプリ使用統計を記録しました (デバイス: {DEVICE_ID})")


def scan_and_report():
    """Full scan + report for Android."""
    print(f"=== AppPulse Android スキャン ({DEVICE_ID}) ===\n")

    # Get installed packages
    packages = get_installed_packages()
    print(f"インストール済みアプリ: {len(packages)} 件")

    # Get usage stats
    poll_android()

    # Show rankings
    from tracker.usage_aggregator import get_top_apps, get_bottom_apps, format_duration
    top = get_top_apps(n=5, days=7)
    bottom = get_bottom_apps(n=5, days=7)

    if top:
        print(f"\n最も使用しているアプリ:")
        for a in top:
            print(f"  {a['process_name']}: {format_duration(a['total_foreground_seconds'])}")

    if bottom:
        print(f"\n最も使用していないアプリ:")
        for a in bottom:
            print(f"  {a['process_name']}: {format_duration(a['total_foreground_seconds'])}")

    # Sync
    try:
        from storage.sync import export_stats
        export_stats()
        print(f"\n同期データをエクスポートしました")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="AppPulse Android Tracker")
    parser.add_argument("--poll", action="store_true",
                        help="1回だけ使用統計を取得")
    args = parser.parse_args()

    init_db()

    if args.poll:
        poll_android()
    else:
        scan_and_report()


if __name__ == "__main__":
    main()
