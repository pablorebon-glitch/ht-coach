from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ht_coach_app.core.backups import create_data_backup
from ht_coach_app.core.paths import application_paths, installed_user_data_dir


PORTABLE_DATA_FILES = (
    "historical_matches.json",
    "weekly_training_planner.json",
    "opponents.json",
    "season_calendar.json",
    "app_settings.json",
    "match_workspace.json",
    "match_last_result.json",
)


@dataclass(frozen=True)
class DataImportPlan:
    source_dir: Path
    destination_dir: Path
    files: tuple[Path, ...]
    backup_dir: Path | None = None

    @property
    def has_files(self):
        return bool(self.files)


def ensure_portable_writable(paths=None):
    paths = paths or application_paths()
    if not paths.is_portable:
        return True
    try:
        paths.ensure_writable_dirs()
        probe = paths.data_dir / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def installed_data_dir():
    return installed_user_data_dir()


def build_import_plan(source_dir, paths=None):
    paths = paths or application_paths()
    source = Path(source_dir).expanduser().resolve()
    files = tuple(
        source / filename
        for filename in PORTABLE_DATA_FILES
        if (source / filename).exists()
    )
    if (source / "rosters").exists():
        files = files + (source / "rosters",)
    return DataImportPlan(
        source_dir=source,
        destination_dir=paths.data_dir,
        files=files,
    )


def portable_data_is_empty(paths=None):
    paths = paths or application_paths()
    if not paths.data_dir.exists():
        return True
    for item in paths.data_dir.iterdir():
        if item.name.startswith("."):
            continue
        if item.is_file() or any(item.iterdir()):
            return False
    return True


def import_data_directory(source_dir, reason="data_import", paths=None):
    paths = paths or application_paths()
    plan = build_import_plan(source_dir, paths=paths)
    if not plan.has_files:
        return plan
    backup = create_data_backup(reason, paths=paths)
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    for source in plan.files:
        destination = paths.data_dir / source.name
        if source.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    return DataImportPlan(
        source_dir=plan.source_dir,
        destination_dir=plan.destination_dir,
        files=plan.files,
        backup_dir=backup,
    )


def portable_roster_copy(source_path, paths=None, now=None):
    paths = paths or application_paths()
    source = Path(source_path)
    if not paths.is_portable or not source.exists():
        return str(source_path)
    try:
        source.resolve().relative_to(paths.root_dir.resolve())
        return paths.relative_to_root(source)
    except (OSError, ValueError):
        pass
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    safe_name = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_"
        for char in source.name
    )
    destination = paths.rosters_dir / f"{timestamp}_{safe_name}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return paths.relative_to_root(destination)
