import subprocess
import re


def _run_winget(*args, timeout=60):
    cmd = ["winget"] + list(args) + [
        "--accept-source-agreements",
        "--disable-interactivity",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace",
    )
    return result


def _parse_table(output):
    """Parse winget's fixed-width table output into list of dicts."""
    lines = output.strip().splitlines()
    # Find the separator line (contains dashes)
    sep_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^[\-\s]+$", line) and len(line) > 10:
            sep_idx = i
            break
    if sep_idx is None or sep_idx == 0:
        return []

    header_line = lines[sep_idx - 1]
    sep_line = lines[sep_idx]

    # Determine column positions from separator
    col_positions = []
    in_dash = False
    start = 0
    for i, ch in enumerate(sep_line):
        if ch == "-" and not in_dash:
            start = i
            in_dash = True
        elif ch != "-" and in_dash:
            col_positions.append((start, i))
            in_dash = False
    if in_dash:
        col_positions.append((start, len(sep_line)))

    # Extract column names
    col_names = []
    for s, e in col_positions:
        col_names.append(header_line[s:e].strip())

    # Parse data rows
    rows = []
    for line in lines[sep_idx + 1:]:
        if not line.strip():
            continue
        row = {}
        for name, (s, e) in zip(col_names, col_positions):
            row[name] = line[s:e].strip() if s < len(line) else ""
        rows.append(row)
    return rows


def list_installed():
    """Return list of dicts with installed app info."""
    result = _run_winget("list")
    if result.returncode != 0:
        return []
    return _parse_table(result.stdout)


def install_app(app_id):
    """Install an app by winget ID. Returns (success, output)."""
    result = _run_winget("install", "--id", app_id, "--silent",
                         timeout=300)
    return result.returncode == 0, result.stdout + result.stderr


def uninstall_app(app_id=None, app_name=None):
    """Uninstall an app. Returns (success, output)."""
    if app_id:
        result = _run_winget("uninstall", "--id", app_id, "--silent",
                             timeout=120)
    elif app_name:
        result = _run_winget("uninstall", "--name", app_name, "--silent",
                             timeout=120)
    else:
        return False, "No app_id or app_name provided"
    return result.returncode == 0, result.stdout + result.stderr


def search_app(query):
    """Search winget for apps. Returns list of dicts."""
    result = _run_winget("search", query)
    if result.returncode != 0:
        return []
    return _parse_table(result.stdout)
