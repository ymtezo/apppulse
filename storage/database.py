import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

from config import DB_PATH


_local = threading.local()


def _get_connection():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def get_db():
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                process_name TEXT NOT NULL,
                exe_path TEXT,
                device_id TEXT NOT NULL,
                is_foreground INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 60
            );

            CREATE TABLE IF NOT EXISTS installed_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                winget_id TEXT,
                exe_path TEXT,
                install_date TEXT,
                device_id TEXT NOT NULL,
                last_seen TEXT,
                UNIQUE(app_name, device_id)
            );

            CREATE TABLE IF NOT EXISTS deletion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                app_name TEXT NOT NULL,
                winget_id TEXT,
                exe_path TEXT,
                device_id TEXT NOT NULL,
                reason TEXT,
                usage_rank INTEGER,
                total_foreground_seconds INTEGER,
                uninstall_method TEXT,
                success INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS usage_stats (
                process_name TEXT NOT NULL,
                device_id TEXT NOT NULL,
                total_launches INTEGER DEFAULT 0,
                total_foreground_seconds INTEGER DEFAULT 0,
                last_used TEXT,
                first_seen TEXT,
                PRIMARY KEY (process_name, device_id)
            );

            CREATE TABLE IF NOT EXISTS uninstall_rejections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                app_name TEXT NOT NULL,
                device_id TEXT NOT NULL,
                stage TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_usage_events_process
                ON usage_events(process_name);
            CREATE INDEX IF NOT EXISTS idx_usage_events_timestamp
                ON usage_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_usage_events_device
                ON usage_events(device_id);
            CREATE INDEX IF NOT EXISTS idx_rejections_app
                ON uninstall_rejections(app_name, device_id);
        """)


# --- usage_events CRUD ---

def insert_usage_event(process_name, exe_path, device_id, is_foreground,
                       duration_seconds=60):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO usage_events
               (timestamp, process_name, exe_path, device_id, is_foreground,
                duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), process_name, exe_path, device_id,
             int(is_foreground), duration_seconds),
        )


def insert_usage_events_batch(events):
    """events: list of (process_name, exe_path, device_id, is_foreground)"""
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.executemany(
            """INSERT INTO usage_events
               (timestamp, process_name, exe_path, device_id, is_foreground,
                duration_seconds)
               VALUES (?, ?, ?, ?, ?, 60)""",
            [(now, name, path, dev, int(fg)) for name, path, dev, fg in events],
        )


def get_usage_events(device_id=None, days=30):
    cutoff = datetime.now()
    cutoff = cutoff.replace(day=max(1, cutoff.day - days) if days < 28 else 1)
    sql = "SELECT * FROM usage_events WHERE timestamp >= ?"
    params = [cutoff.isoformat()]
    if device_id:
        sql += " AND device_id = ?"
        params.append(device_id)
    sql += " ORDER BY timestamp DESC"
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


# --- usage_stats CRUD ---

def upsert_usage_stats(process_name, device_id, foreground_seconds,
                       launches=0):
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO usage_stats
               (process_name, device_id, total_launches,
                total_foreground_seconds, last_used, first_seen)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(process_name, device_id) DO UPDATE SET
                   total_launches = total_launches + excluded.total_launches,
                   total_foreground_seconds = total_foreground_seconds
                       + excluded.total_foreground_seconds,
                   last_used = excluded.last_used""",
            (process_name, device_id, launches, foreground_seconds, now, now),
        )


def get_all_usage_stats(device_id=None):
    sql = "SELECT * FROM usage_stats"
    params = []
    if device_id:
        sql += " WHERE device_id = ?"
        params.append(device_id)
    sql += " ORDER BY total_foreground_seconds DESC"
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


# --- installed_apps CRUD ---

def upsert_installed_app(app_name, device_id, winget_id=None, exe_path=None,
                         install_date=None):
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO installed_apps
               (app_name, winget_id, exe_path, install_date, device_id,
                last_seen)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(app_name, device_id) DO UPDATE SET
                   winget_id = COALESCE(excluded.winget_id, winget_id),
                   exe_path = COALESCE(excluded.exe_path, exe_path),
                   last_seen = excluded.last_seen""",
            (app_name, winget_id, exe_path, install_date, device_id, now),
        )


def get_installed_apps(device_id=None):
    sql = "SELECT * FROM installed_apps"
    params = []
    if device_id:
        sql += " WHERE device_id = ?"
        params.append(device_id)
    sql += " ORDER BY app_name"
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


def remove_installed_app(app_name, device_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM installed_apps WHERE app_name = ? AND device_id = ?",
            (app_name, device_id),
        )


# --- deletion_log CRUD ---

def insert_deletion_log(app_name, device_id, reason, winget_id=None,
                        exe_path=None, usage_rank=None,
                        total_foreground_seconds=None,
                        uninstall_method=None, success=True):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO deletion_log
               (timestamp, app_name, winget_id, exe_path, device_id, reason,
                usage_rank, total_foreground_seconds, uninstall_method, success)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), app_name, winget_id, exe_path,
             device_id, reason, usage_rank, total_foreground_seconds,
             uninstall_method, int(success)),
        )


def get_deletion_log(device_id=None):
    sql = "SELECT * FROM deletion_log"
    params = []
    if device_id:
        sql += " WHERE device_id = ?"
        params.append(device_id)
    sql += " ORDER BY timestamp DESC"
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


# --- uninstall_rejections CRUD ---

def insert_rejection(app_name, device_id, stage="first"):
    """Record that the user rejected an uninstall.

    stage: 'first' (1回目の確認で拒否) or 'final' (最終確認で拒否)
    """
    with get_db() as conn:
        conn.execute(
            """INSERT INTO uninstall_rejections
               (timestamp, app_name, device_id, stage)
               VALUES (?, ?, ?, ?)""",
            (datetime.now().isoformat(), app_name, device_id, stage),
        )


def get_rejection_count(app_name, device_id):
    """Get total rejection count for an app."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM uninstall_rejections
               WHERE app_name = ? AND device_id = ?""",
            (app_name, device_id),
        ).fetchone()
        return row["cnt"] if row else 0


def get_all_rejections(device_id=None):
    """Get rejection counts grouped by app."""
    sql = """SELECT app_name, COUNT(*) as rejection_count,
                    MAX(timestamp) as last_rejected
             FROM uninstall_rejections"""
    params = []
    if device_id:
        sql += " WHERE device_id = ?"
        params.append(device_id)
    sql += " GROUP BY app_name ORDER BY rejection_count DESC"
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()
