"""Alpha 0.6.7 HF-03, Parts 13-16: crash diagnostics, structured logging,
recovery snapshots.
"""
import sys

import pytest

from ht_coach_app.diagnostics.app_context import (
    current_context,
    reset_context,
    update_context,
)
from ht_coach_app.diagnostics.crash_reporter import write_crash_report
from ht_coach_app.diagnostics.event_buffer import (
    AppEvent,
    record_event,
    recent_events,
    reset_event_buffer,
)
from ht_coach_app.diagnostics.recovery_snapshot import RecoverySnapshotStore


@pytest.fixture(autouse=True)
def _reset_diagnostics():
    reset_context()
    reset_event_buffer()
    yield
    reset_context()
    reset_event_buffer()


def test_record_event_stores_action_and_outcome():
    record_event("create_new_match", "provisional:1", "ok")
    events = recent_events()
    assert len(events) == 1
    assert events[0].action == "create_new_match"
    assert events[0].match_record_id == "provisional:1"
    assert events[0].outcome == "ok"


def test_event_buffer_keeps_only_the_last_20():
    for i in range(25):
        record_event("analyze", f"record-{i}")
    events = recent_events()
    assert len(events) == 20
    assert events[0].match_record_id == "record-5"
    assert events[-1].match_record_id == "record-24"


def test_event_never_carries_fields_for_raw_personal_data():
    field_names = set(AppEvent.__dataclass_fields__)
    assert field_names == {"timestamp", "action", "match_record_id", "outcome", "detail"}


def test_update_context_merges_changes():
    update_context(active_page="match", opponent_name="CA Chaco")
    context = current_context()
    assert context.active_page == "match"
    assert context.opponent_name == "CA Chaco"


def test_reset_context_clears_everything():
    update_context(active_page="match", opponent_name="CA Chaco")
    reset_context()
    context = current_context()
    assert context.active_page == ""
    assert context.opponent_name == ""


def test_crash_log_includes_all_required_fields(tmp_path):
    update_context(
        active_page="match", active_match_record_id="provisional:1",
        opponent_name="CA Chaco", official_match_id="770918226",
        current_action="analyze", source_csv="players.csv", workspace_dirty=True,
    )
    record_event("create_new_match", "provisional:1")
    record_event("analyze", "provisional:1")

    try:
        raise ValueError("simulated crash for testing")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        log_path = write_crash_report(exc_type, exc_value, exc_tb, directory=tmp_path / "crashes")

    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "app_version" in text
    assert "python_version" in text
    assert "platform" in text
    assert "active_page: match" in text
    assert "active_match_record_id: provisional:1" in text
    assert "opponent: CA Chaco" in text
    assert "official_match_id: 770918226" in text
    assert "current_action: analyze" in text
    assert "source_csv: players.csv" in text
    assert "workspace_dirty: True" in text
    assert "ValueError: simulated crash for testing" in text
    assert "last_20_events" in text
    assert "create_new_match" in text


def test_crash_log_filename_matches_the_briefs_own_pattern(tmp_path):
    try:
        raise ValueError("x")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        log_path = write_crash_report(exc_type, exc_value, exc_tb, directory=tmp_path / "crashes")

    assert log_path.name.startswith("crash_")
    assert log_path.name.endswith(".log")


def test_crash_reporter_never_raises_even_for_a_nested_missing_directory(tmp_path):
    unwritable = tmp_path / "not_a_real_dir" / "nested" / "deeply"
    try:
        raise ValueError("x")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        log_path = write_crash_report(exc_type, exc_value, exc_tb, directory=unwritable)
    assert log_path is not None


def test_recovery_snapshot_stores_and_loads(tmp_path):
    store = RecoverySnapshotStore(directory=tmp_path / "recovery")
    store.save("provisional:1", tactic="Pressing", team_attitude="Normal")

    loaded = store.load("provisional:1")
    assert loaded["tactic"] == "Pressing"
    assert loaded["team_attitude"] == "Normal"


def test_recovery_snapshot_only_keeps_the_latest_per_record(tmp_path):
    store = RecoverySnapshotStore(directory=tmp_path / "recovery")
    store.save("provisional:1", tactic="Normal")
    store.save("provisional:1", tactic="Counter-Attacks")

    loaded = store.load("provisional:1")
    assert loaded["tactic"] == "Counter-Attacks"


def test_recovery_snapshot_discard_removes_it(tmp_path):
    store = RecoverySnapshotStore(directory=tmp_path / "recovery")
    store.save("provisional:1", tactic="Normal")
    assert store.has_recovery_snapshot("provisional:1")

    store.discard("provisional:1")
    assert not store.has_recovery_snapshot("provisional:1")


def test_recovery_snapshot_missing_record_returns_none(tmp_path):
    store = RecoverySnapshotStore(directory=tmp_path / "recovery")
    assert store.load("never-saved") is None


def test_recovery_snapshot_load_has_no_side_effects(tmp_path):
    store = RecoverySnapshotStore(directory=tmp_path / "recovery")
    store.save("provisional:1", tactic="Pressing")
    loaded = store.load("provisional:1")
    assert loaded is not None
    assert store.has_recovery_snapshot("provisional:1")
