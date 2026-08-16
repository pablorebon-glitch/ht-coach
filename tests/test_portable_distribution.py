import json
from datetime import datetime
from pathlib import Path

import pytest

from ht_coach_app.core.json_io import write_json_atomic
from ht_coach_app.core.paths import (
    ApplicationPaths,
    application_paths,
    configure_application_paths,
)
from ht_coach_app.core.portable import (
    build_import_plan,
    import_data_directory,
    portable_roster_copy,
)
from ht_coach_app.core.version import APP_DISPLAY_NAME, APP_VERSION


@pytest.fixture(autouse=True)
def restore_application_paths():
    configure_application_paths(ApplicationPaths.detect(executable_dir=Path.cwd()))
    yield
    configure_application_paths(ApplicationPaths.detect(executable_dir=Path.cwd()))


def test_portable_flag_enables_portable_paths(tmp_path):
    root = tmp_path / "HT Coach Portable"
    root.mkdir()
    (root / "portable.flag").write_text("", encoding="utf-8")

    paths = ApplicationPaths.detect(executable_dir=root)

    assert paths.is_portable is True
    assert paths.data_dir == root / "data"
    assert paths.backup_dir == root / "backups"
    assert paths.log_dir == root / "logs"


def test_missing_flag_uses_development_data_dir(tmp_path, monkeypatch):
    root = tmp_path / "dev"
    root.mkdir()
    local = tmp_path / "localappdata"
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    paths = ApplicationPaths.detect(executable_dir=root)

    assert paths.is_portable is False
    assert paths.data_dir == local / "HT Coach" / "Alpha"


def test_portable_paths_create_writable_directories(tmp_path):
    root = tmp_path / "portable"
    root.mkdir()
    (root / "portable.flag").write_text("", encoding="utf-8")
    paths = ApplicationPaths.detect(executable_dir=root)

    paths.ensure_writable_dirs()

    assert paths.rosters_dir.exists()
    assert paths.crash_log_dir.exists()
    assert paths.recovery_log_dir.exists()


def test_atomic_json_write_preserves_valid_file(tmp_path):
    path = tmp_path / "settings.json"

    write_json_atomic(path, {"language": "es"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"language": "es"}
    assert not (tmp_path / ".settings.json.tmp").exists()


def test_import_plan_and_data_copy_with_backup(tmp_path):
    source = tmp_path / "appdata"
    source.mkdir()
    (source / "opponents.json").write_text("[]", encoding="utf-8")
    (source / "weekly_training_planner.json").write_text("{}", encoding="utf-8")
    root = tmp_path / "portable"
    root.mkdir()
    (root / "portable.flag").write_text("", encoding="utf-8")
    paths = ApplicationPaths.detect(executable_dir=root)
    paths.ensure_writable_dirs()
    (paths.data_dir / "opponents.json").write_text("[{\"name\":\"Old\"}]", encoding="utf-8")

    plan = build_import_plan(source, paths=paths)
    result = import_data_directory(source, paths=paths)

    assert [item.name for item in plan.files] == [
        "weekly_training_planner.json",
        "opponents.json",
    ]
    assert (paths.data_dir / "opponents.json").read_text(encoding="utf-8") == "[]"
    assert result.backup_dir is not None
    assert (result.backup_dir / "opponents.json").exists()


def test_portable_roster_copy_uses_relative_path(tmp_path):
    root = tmp_path / "portable"
    root.mkdir()
    (root / "portable.flag").write_text("", encoding="utf-8")
    paths = ApplicationPaths.detect(executable_dir=root)
    configure_application_paths(paths)
    source = tmp_path / "downloads" / "players.csv"
    source.parent.mkdir()
    source.write_text("Name\nPlayer One\n", encoding="utf-8")

    stored = portable_roster_copy(
        source,
        paths=paths,
        now=datetime(2026, 8, 4, 10, 30, 0),
    )

    assert stored == "data/rosters/2026-08-04_10-30-00_players.csv"
    assert (root / stored).exists()
    assert not Path(stored).is_absolute()


def test_relative_portable_path_resolves_after_root_changes(tmp_path):
    root_a = tmp_path / "A" / "HT Coach Portable"
    root_b = tmp_path / "B" / "HT Coach Portable"
    (root_a / "data" / "rosters").mkdir(parents=True)
    (root_a / "portable.flag").write_text("", encoding="utf-8")
    relative = Path("data/rosters/players.csv")
    (root_a / relative).write_text("Name\nPlayer One\n", encoding="utf-8")
    root_b.parent.mkdir()
    import shutil

    shutil.copytree(root_a, root_b)

    moved_paths = ApplicationPaths.detect(executable_dir=root_b)

    assert moved_paths.resolve_user_path(relative) == root_b / relative


def test_version_source_is_alpha_069_portable():
    assert APP_VERSION == "Alpha 0.6.9 Portable"
    assert APP_DISPLAY_NAME == "HT Coach Alpha 0.6.9 Portable"


def test_configure_application_paths_roundtrip(tmp_path):
    root = tmp_path / "portable"
    root.mkdir()
    (root / "portable.flag").write_text("", encoding="utf-8")
    paths = ApplicationPaths.detect(executable_dir=root)

    configure_application_paths(paths)

    assert application_paths().is_portable is True
    assert application_paths().data_dir == root / "data"
