from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


PORTABLE_FLAG = "portable.flag"


def project_root():
    return Path(__file__).resolve().parents[2]


def _installed_data_dir():
    base_path = os.environ.get("LOCALAPPDATA")
    if base_path:
        return Path(base_path) / "HT Coach" / "Alpha"
    return Path.home() / ".ht-coach" / "alpha"


def _executable_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def _bundle_resource_root():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return project_root()


@dataclass(frozen=True)
class ApplicationPaths:
    root_dir: Path
    data_dir: Path
    backup_dir: Path
    log_dir: Path
    resource_dir: Path
    licenses_dir: Path
    is_portable: bool = False

    @classmethod
    def detect(cls, executable_dir=None):
        root = Path(executable_dir).resolve() if executable_dir else _executable_dir()
        portable = (root / PORTABLE_FLAG).exists()
        resource_root = _bundle_resource_root()
        if portable:
            return cls(
                root_dir=root,
                data_dir=root / "data",
                backup_dir=root / "backups",
                log_dir=root / "logs",
                resource_dir=(
                    root / "resources"
                    if (root / "resources").exists()
                    else resource_root / "resources"
                ),
                licenses_dir=root / "licenses",
                is_portable=True,
            )
        return cls(
            root_dir=root,
            data_dir=_installed_data_dir(),
            backup_dir=_installed_data_dir() / "backups",
            log_dir=_installed_data_dir() / "logs",
            resource_dir=resource_root / "resources",
            licenses_dir=resource_root / "licenses",
            is_portable=False,
        )

    @property
    def migrations_dir(self):
        return self.data_dir / "migrations"

    @property
    def rosters_dir(self):
        return self.data_dir / "rosters"

    @property
    def crash_log_dir(self):
        return self.log_dir / "crashes"

    @property
    def recovery_log_dir(self):
        return self.log_dir / "recovery"

    def ensure_writable_dirs(self):
        for path in (
            self.data_dir,
            self.migrations_dir,
            self.rosters_dir,
            self.backup_dir,
            self.log_dir,
            self.crash_log_dir,
            self.recovery_log_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def relative_to_root(self, path):
        path = Path(path)
        try:
            return path.resolve().relative_to(self.root_dir.resolve()).as_posix()
        except (OSError, ValueError):
            return str(path)

    def resolve_user_path(self, value):
        text = str(value or "").strip()
        if not text:
            return Path()
        path = Path(text)
        if path.is_absolute():
            return path
        if self.is_portable:
            return self.root_dir / path
        return path


_APPLICATION_PATHS = None


def application_paths():
    global _APPLICATION_PATHS
    if _APPLICATION_PATHS is None:
        _APPLICATION_PATHS = ApplicationPaths.detect()
    return _APPLICATION_PATHS


def configure_application_paths(paths=None, executable_dir=None):
    global _APPLICATION_PATHS
    _APPLICATION_PATHS = paths or ApplicationPaths.detect(executable_dir=executable_dir)
    return _APPLICATION_PATHS


def assets_dir():
    return application_paths().resource_dir / "assets"


def resources_dir():
    return application_paths().resource_dir


def application_icon_path():
    for filename in ("app_icon.ico", "app_icon.png"):
        path = assets_dir() / filename
        if path.exists():
            return path
    return None


def user_data_dir():
    return application_paths().data_dir


def installed_user_data_dir():
    return _installed_data_dir()


def logs_dir():
    return application_paths().log_dir


def backups_dir():
    return application_paths().backup_dir


def historical_match_snapshots_path():
    return user_data_dir() / "historical_matches.json"
