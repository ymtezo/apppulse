#!/usr/bin/env python3
"""Generate OTA version.json from app/build.gradle.kts."""
import argparse
import json
import re
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-gradle",
        default="app/build.gradle.kts",
        help="Path to app build.gradle.kts",
    )
    parser.add_argument(
        "--apk-url",
        default="https://github.com/ymtezo/apppulse-android/releases/latest/download/app-release.apk",
        help="URL to the release APK",
    )
    parser.add_argument("--out", default="version.json", help="Output file path")
    args = parser.parse_args()

    gradle = Path(args.build_gradle).read_text(encoding="utf-8")
    version_code_match = re.search(r"versionCode\s*=\s*(\d+)", gradle)
    version_name_match = re.search(r'versionName\s*=\s*"([^"]+)"', gradle)

    if not version_code_match or not version_name_match:
        print("Could not find versionCode or versionName in build.gradle.kts", file=sys.stderr)
        return 1

    version_code = int(version_code_match.group(1))
    version_name = version_name_match.group(1)

    data = {
        "version_code": version_code,
        "version_name": version_name,
        "apk_url": args.apk_url,
    }

    Path(args.out).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Generated {args.out}: {data}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
