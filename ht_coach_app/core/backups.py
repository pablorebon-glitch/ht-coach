from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ht_coach_app.core.paths import application_paths


def create_data_backup(reason, paths=None, max_backups=10):
    paths = paths or application_paths()
    if not paths.data_dir.exists():
        return None
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_reason = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in str(reason or "backup")
    ).strip("_") or "backup"
    destination = paths.backup_dir / f"{stamp}_{safe_reason}"
    shutil.copytree(paths.data_dir, destination)
    prune_backups(paths.backup_dir, max_backups=max_backups)
    return destination


def prune_backups(backup_dir, max_backups=10):
    backup_dir = Path(backup_dir)
    if max_backups <= 0 or not backup_dir.exists():
        return
    backups = sorted(
        (item for item in backup_dir.iterdir() if item.is_dir()),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for old in backups[max_backups:]:
        shutil.rmtree(old, ignore_errors=True)

