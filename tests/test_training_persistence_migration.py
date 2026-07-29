import json

from engine.weekly_training.persistence import WeeklyTrainingRepository
from engine.weekly_training.training_rules import rule_provider_for
from engine.weekly_training.training_types import TrainingType
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService


def test_legacy_file_with_no_training_type_defaults_to_playmaking(tmp_path):
    path = tmp_path / "planner.json"
    path.write_text(json.dumps({"priorities": {}, "match_records": []}), encoding="utf-8")

    repository = WeeklyTrainingRepository(path)
    state = repository.load()

    assert state.active_training_type == TrainingType.PLAYMAKING.value


def test_explicit_training_type_is_never_overwritten_by_the_default(tmp_path):
    path = tmp_path / "planner.json"
    path.write_text(
        json.dumps({"active_training_type": "DEFENDING", "priorities": {}, "match_records": []}),
        encoding="utf-8",
    )

    repository = WeeklyTrainingRepository(path)
    state = repository.load()

    assert state.active_training_type == "DEFENDING"


def test_unknown_future_training_type_does_not_crash_load(tmp_path):
    path = tmp_path / "planner.json"
    path.write_text(
        json.dumps(
            {
                "active_training_type": "SOME_FUTURE_TYPE_NOT_YET_SUPPORTED",
                "priorities": {},
                "match_records": [],
            }
        ),
        encoding="utf-8",
    )

    repository = WeeklyTrainingRepository(path)
    state = repository.load()

    # No crash, no silent data loss — the unrecognized value is preserved
    # as-is; only *using* it for rules degrades safely.
    assert state.active_training_type == "SOME_FUTURE_TYPE_NOT_YET_SUPPORTED"
    assert rule_provider_for(state.active_training_type) is None

    service = WeeklyTrainingAppService(repository=repository)
    assert service.active_training_rules() is None
    # coverage() must not crash even though there are no rules to apply
    assert service.coverage([]) == ()


def test_all_twelve_training_types_round_trip_through_persistence(tmp_path):
    for training_type in TrainingType:
        path = tmp_path / f"planner_{training_type.value}.json"
        repository = WeeklyTrainingRepository(path)
        state = repository.load()
        from dataclasses import replace

        state = replace(state, active_training_type=training_type.value)
        repository.save(state)

        reloaded = repository.load()
        assert reloaded.active_training_type == training_type.value
        assert rule_provider_for(reloaded.active_training_type) is not None


def test_unrelated_data_survives_alongside_an_unknown_training_type(tmp_path):
    """No silent data deletion: priorities and match records already
    saved must survive even when active_training_type is something this
    build doesn't recognize."""
    path = tmp_path / "planner.json"
    repository = WeeklyTrainingRepository(path)
    state = repository.load()

    from engine.weekly_training.models import TrainingPriority, TrainingPriorityRecord

    state = repository.save_priority(
        state,
        TrainingPriorityRecord(
            player_id="p1",
            player_name="Test Player",
            priority=TrainingPriority.REQUIRED_100,
        ),
    )

    from dataclasses import replace

    state = replace(state, active_training_type="SOME_FUTURE_TYPE")
    repository.save(state)

    reloaded = repository.load()
    assert reloaded.priorities["p1"].priority == TrainingPriority.REQUIRED_100
    assert reloaded.active_training_type == "SOME_FUTURE_TYPE"


def test_serialization_is_deterministic():
    """Saving the same state twice produces byte-identical JSON."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path_a = Path(tmp) / "a.json"
        path_b = Path(tmp) / "b.json"
        for path in (path_a, path_b):
            repository = WeeklyTrainingRepository(path)
            state = repository.load()
            from dataclasses import replace

            state = replace(state, active_training_type="DEFENDING")
            repository.save(state)

        assert path_a.read_text(encoding="utf-8") == path_b.read_text(encoding="utf-8")
