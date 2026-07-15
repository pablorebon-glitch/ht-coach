from pathlib import Path


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

