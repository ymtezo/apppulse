import os
import socket

APP_NAME = "AppPulse"
DEVICE_ID = socket.gethostname()

# Paths
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)
DB_PATH = os.path.join(APPDATA_DIR, "apppulse.db")

# Ensure data directory exists
os.makedirs(APPDATA_DIR, exist_ok=True)

# Tracker settings
POLL_INTERVAL_SECONDS = 60
SESSION_GAP_SECONDS = 300  # 5 min gap = new session

# Ranking weights
WEIGHT_FOREGROUND_TIME = 0.5
WEIGHT_LAUNCHES = 0.3
WEIGHT_RECENCY = 0.2

# System processes to exclude from tracking
SYSTEM_PROCESS_EXCLUSIONS = frozenset({
    "svchost.exe", "csrss.exe", "smss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "winlogon.exe", "dwm.exe", "fontdrvhost.exe", "conhost.exe",
    "RuntimeBroker.exe", "SearchHost.exe", "StartMenuExperienceHost.exe",
    "TextInputHost.exe", "ShellExperienceHost.exe", "sihost.exe",
    "taskhostw.exe", "ctfmon.exe", "dllhost.exe", "WmiPrvSE.exe",
    "SecurityHealthSystray.exe", "SecurityHealthService.exe",
    "MsMpEng.exe", "NisSrv.exe", "Registry", "System", "Idle",
    "spoolsv.exe", "SearchIndexer.exe", "SystemSettingsBroker.exe",
    "backgroundTaskHost.exe", "audiodg.exe", "CompPkgSrv.exe",
    "UserOOBEBroker.exe", "WidgetService.exe", "Widgets.exe",
})

# Apps that must never be uninstalled
UNINSTALL_BLOCKLIST = frozenset({
    "Microsoft.WindowsTerminal",
    "Microsoft.DesktopAppInstaller",
    "Microsoft.WindowsStore",
    "Microsoft.Windows.Explorer",
    "Microsoft.Edge",
    "Microsoft.VCRedist",
    "Microsoft.DotNet",
    "Microsoft.PowerShell",
})

# Sync settings
ONEDRIVE_DIR = os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive")
SYNC_DIR = os.path.join(ONEDRIVE_DIR, APP_NAME, "sync")
SYNC_INTERVAL_SECONDS = 6 * 3600  # 6 hours

# Notification settings
NOTIFICATION_INTERVAL_DAYS = 7  # Weekly recommendations
