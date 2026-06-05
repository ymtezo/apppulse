"""AppPulse デバイスセットアップ

このスクリプトを各デバイスで実行すると:
1. 依存パッケージをインストール
2. DBを初期化
3. Windows Task Schedulerに週次タスク（毎週土曜10:00）を登録
4. 初回スキャンを実行

使い方:
    python setup_device.py          # セットアップ
    python setup_device.py --remove # タスク削除
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TASK_NAME = "AppPulse_WeeklyReport"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def install_deps():
    print("[1/4] 依存パッケージをインストール中...")
    req = os.path.join(PROJECT_DIR, "requirements.txt")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("  OK")
    else:
        print(f"  失敗: {result.stderr[:200]}")
        return False
    return True


def init_database():
    print("[2/4] データベースを初期化中...")
    from storage.database import init_db
    init_db()
    from config import DB_PATH
    print(f"  OK: {DB_PATH}")


def register_scheduled_task():
    print("[3/4] 週次タスクを登録中...")
    python_path = sys.executable
    script_path = os.path.join(PROJECT_DIR, "weekly_report.py")

    # Remove existing task first (ignore errors)
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
    )

    # Create task: every Saturday at 10:00
    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", f'"{python_path}" "{script_path}"',
            "/SC", "WEEKLY",
            "/D", "SAT",
            "/ST", "10:00",
            "/RL", "LIMITED",
            "/F",
        ],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("  OK: 毎週土曜 10:00 に実行")
    else:
        print(f"  失敗: {result.stderr[:300]}")
        print("  手動で登録する場合:")
        print(f'    schtasks /Create /TN "{TASK_NAME}" '
              f'/TR "\\"{python_path}\\" \\"{script_path}\\"" '
              f'/SC WEEKLY /D SAT /ST 10:00')
        return False
    return True


def remove_scheduled_task():
    print("週次タスクを削除中...")
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("  OK: タスク削除完了")
    else:
        print(f"  タスクが見つかりません: {result.stderr[:200]}")


def initial_scan():
    print("[4/4] 初回スキャンを実行中...")
    from manager.app_inventory import scan_installed_apps
    from config import DEVICE_ID
    apps = scan_installed_apps()
    print(f"  OK: {len(apps)} 件のアプリを検出 (デバイス: {DEVICE_ID})")


def main():
    parser = argparse.ArgumentParser(description="AppPulse デバイスセットアップ")
    parser.add_argument("--remove", action="store_true",
                        help="スケジュールタスクを削除")
    args = parser.parse_args()

    if args.remove:
        remove_scheduled_task()
        return

    print(f"=== AppPulse セットアップ ===")
    print(f"プロジェクト: {PROJECT_DIR}")
    print()

    if not install_deps():
        print("\n依存パッケージのインストールに失敗しました。")
        return

    init_database()
    success = register_scheduled_task()
    initial_scan()

    print()
    print("=== セットアップ完了 ===")
    if success:
        print("毎週土曜 10:00 に週次レポートが自動実行されます。")
    print()
    print("使い方:")
    print(f"  python {os.path.join(PROJECT_DIR, 'main.py')}              # 通常起動")
    print(f"  python {os.path.join(PROJECT_DIR, 'main.py')} --dashboard  # ダッシュボード")
    print(f"  python {os.path.join(PROJECT_DIR, 'weekly_report.py')}     # 手動で週次レポート")


if __name__ == "__main__":
    main()
