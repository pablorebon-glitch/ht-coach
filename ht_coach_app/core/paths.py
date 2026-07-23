from pathlib import Path
import os


def project_root():
    return Path(__file__).resolve().parents[2]


def assets_dir():
    return project_root() / "assets"


def application_icon_path():
    for filename in ("app_icon.ico", "app_icon.png"):
        path = assets_dir() / filename
        if path.exists():
            return path

    return None


def user_data_dir():
    base_path = os.environ.get("LOCALAPPDATA")

    if base_path:
        return Path(base_path) / "HT Coach" / "Alpha"

    return Path.home() / ".ht-coach" / "alpha"


def historical_match_snapshots_path():
    return user_data_dir() / "historical_matches.json"
