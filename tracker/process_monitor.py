import ctypes
import ctypes.wintypes
import logging
import threading
import time

import psutil

from config import (
    DEVICE_ID,
    POLL_INTERVAL_SECONDS,
    SYSTEM_PROCESS_EXCLUSIONS,
)
from storage.database import insert_usage_events_batch, upsert_usage_stats

logger = logging.getLogger(__name__)

user32 = ctypes.windll.user32


def _get_foreground_pid():
    """Get the PID of the foreground window's process."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value if pid.value else None


def _snapshot_processes():
    """Take a snapshot of running user processes.

    Returns list of (process_name, exe_path, is_foreground).
    """
    fg_pid = _get_foreground_pid()
    seen = set()
    results = []

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = proc.info
            name = info["name"]
            if not name or name in SYSTEM_PROCESS_EXCLUSIONS:
                continue
            if name in seen:
                continue
            seen.add(name)

            exe_path = info.get("exe") or ""
            is_fg = info["pid"] == fg_pid
            results.append((name, exe_path, is_fg))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return results


class ProcessMonitor:
    """Background thread that polls running processes."""

    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("ProcessMonitor started (interval=%ds)", POLL_INTERVAL_SECONDS)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("ProcessMonitor stopped")

    @property
    def is_running(self):
        return self._running

    def _poll_loop(self):
        while self._running:
            try:
                self._poll_once()
            except Exception:
                logger.exception("Error during process poll")
            time.sleep(POLL_INTERVAL_SECONDS)

    def _poll_once(self):
        snapshot = _snapshot_processes()
        if not snapshot:
            return

        events = [
            (name, exe_path, DEVICE_ID, is_fg)
            for name, exe_path, is_fg in snapshot
        ]
        insert_usage_events_batch(events)

        # Update aggregated stats for the foreground app
        for name, _exe, is_fg in snapshot:
            if is_fg:
                upsert_usage_stats(
                    name, DEVICE_ID,
                    foreground_seconds=POLL_INTERVAL_SECONDS,
                    launches=0,
                )
                break

    def poll_once_sync(self):
        """Run a single poll synchronously (for testing / manual trigger)."""
        self._poll_once()
