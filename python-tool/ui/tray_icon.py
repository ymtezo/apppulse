import logging
import threading

from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)


def _create_default_icon():
    """Create a simple colored icon programmatically."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Blue circle background
    draw.ellipse([4, 4, 60, 60], fill=(66, 133, 244, 255))
    # White "A" letter
    draw.text((20, 14), "A", fill=(255, 255, 255, 255))
    return img


class TrayIcon:
    """System tray icon for AppPulse."""

    def __init__(self, on_open_dashboard=None, on_quit=None,
                 on_pause_resume=None):
        self._on_open_dashboard = on_open_dashboard
        self._on_quit = on_quit
        self._on_pause_resume = on_pause_resume
        self._paused = False
        self._icon = None
        self._thread = None

    def _build_menu(self):
        pause_label = "トラッキング再開" if self._paused else "トラッキング一時停止"
        return pystray.Menu(
            pystray.MenuItem("ダッシュボードを開く", self._handle_dashboard,
                             default=True),
            pystray.MenuItem(pause_label, self._handle_pause_resume),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", self._handle_quit),
        )

    def _handle_dashboard(self, icon, item):
        if self._on_open_dashboard:
            self._on_open_dashboard()

    def _handle_pause_resume(self, icon, item):
        self._paused = not self._paused
        icon.update_menu()
        if self._on_pause_resume:
            self._on_pause_resume(self._paused)

    def _handle_quit(self, icon, item):
        icon.stop()
        if self._on_quit:
            self._on_quit()

    def start(self):
        image = _create_default_icon()
        self._icon = pystray.Icon(
            "AppPulse",
            image,
            "AppPulse - アプリ使用状況トラッカー",
            menu=self._build_menu(),
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("Tray icon started")

    def stop(self):
        if self._icon:
            self._icon.stop()
        logger.info("Tray icon stopped")
