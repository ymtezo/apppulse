import os
import tempfile
import unittest
from datetime import datetime, timedelta

from manager.uninstaller import is_blocked, uninstall
from tracker.usage_aggregator import _normalize, format_duration
from utils.winget_wrapper import _parse_table
import storage.database as database


class RankingUtilityTests(unittest.TestCase):
    def test_normalize_range_and_equal_values(self):
        self.assertEqual(_normalize([10, 20, 30]), [0.0, 0.5, 1.0])
        self.assertEqual(_normalize([5, 5]), [0.5, 0.5])
        self.assertEqual(_normalize([]), [])

    def test_format_duration(self):
        self.assertEqual(format_duration(59), "59秒")
        self.assertEqual(format_duration(120), "2分")
        self.assertEqual(format_duration(3660), "1時間1分")


class WingetParserTests(unittest.TestCase):
    def test_parse_fixed_width_table(self):
        output = (
            "Name          Id                 Version\n"
            "------------  -----------------  -------\n"
            "Example App   Vendor.Example     1.2.3\n"
        )

        rows = _parse_table(output)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Name"], "Example App")
        self.assertEqual(rows[0]["Id"], "Vendor.Example")


class UninstallGuardTests(unittest.TestCase):
    def test_confirmation_is_required(self):
        success, message = uninstall("Example App", confirmed=False)
        self.assertFalse(success)
        self.assertIn("未確認", message)

    def test_system_apps_are_blocked(self):
        self.assertTrue(is_blocked("Microsoft.WindowsTerminal", "Terminal"))
        self.assertTrue(is_blocked(app_name="Windows Explorer"))
        self.assertFalse(is_blocked("Vendor.OptionalApp", "Optional App"))


class DatabaseWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database.DB_PATH = os.path.join(self.temp_dir.name, "test.db")
        if getattr(database._local, "conn", None) is not None:
            database._local.conn.close()
            database._local.conn = None
        database.init_db()

    def tearDown(self):
        if getattr(database._local, "conn", None) is not None:
            database._local.conn.close()
            database._local.conn = None
        self.temp_dir.cleanup()

    def test_usage_window_uses_elapsed_days(self):
        now = datetime.now()
        with database.get_db() as conn:
            conn.executemany(
                """INSERT INTO usage_events
                   (timestamp, process_name, device_id, is_foreground,
                    duration_seconds)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    ((now - timedelta(hours=12)).isoformat(), "recent.exe", "test", 1, 60),
                    ((now - timedelta(days=3)).isoformat(), "old.exe", "test", 1, 60),
                ],
            )

        rows = database.get_usage_events(device_id="test", days=1)

        self.assertEqual([row["process_name"] for row in rows], ["recent.exe"])


if __name__ == "__main__":
    unittest.main()
