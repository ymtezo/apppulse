import json
import os
from datetime import datetime

from config import APPDATA_DIR, DEVICE_ID
from storage.database import get_deletion_log


LOG_FILE = os.path.join(APPDATA_DIR, "deletion_history.json")


def get_log(device_id=None):
    """Get deletion log from database."""
    rows = get_deletion_log(device_id)
    return [dict(row) for row in rows]


def export_log_to_file(device_id=None):
    """Export deletion log to a JSON file for backup."""
    log = get_log(device_id)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return LOG_FILE


def generate_markdown_report(device_id=None):
    """Generate a markdown deletion report."""
    log = get_log(device_id)
    if not log:
        return "# 削除ログ\n\n削除履歴はありません。\n"

    lines = [
        "# 削除ログ",
        f"\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"デバイス: {device_id or DEVICE_ID}",
        "",
        "| 日時 | アプリ名 | 理由 | 方法 | 結果 |",
        "|------|---------|------|------|------|",
    ]
    for entry in log:
        ts = entry.get("timestamp", "")[:16]
        name = entry.get("app_name", "")
        reason = entry.get("reason", "")
        method = entry.get("uninstall_method", "")
        result = "成功" if entry.get("success") else "失敗"
        lines.append(f"| {ts} | {name} | {reason} | {method} | {result} |")

    return "\n".join(lines)
