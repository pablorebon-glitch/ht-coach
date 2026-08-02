import json

from engine.history.enums import MatchRecordStatus
from engine.history.models import HistoricalMatchSnapshot, MatchContext
from engine.history.repository import HistoricalMatchRepository


def _write_legacy_payload(path, snapshot_dict):
    for key in (
        "retrospective_pre", "provisional_identity", "training_cycle_id",
        "ht_season_number", "ht_season_week",
    ):
        snapshot_dict.pop(key, None)
    path.write_text(
        json.dumps({"schema_version": 1, "snapshots": [snapshot_dict]}),
        encoding="utf-8",
    )


def test_legacy_snapshot_without_alpha_0_6_6_fields_loads_without_loss(tmp_path):
    path = tmp_path / "snapshots.json"
    legacy = HistoricalMatchSnapshot(
        snapshot_id="legacy1",
        match_context=MatchContext(match_date="2026-06-01", official_match_id="700000000"),
    )
    _write_legacy_payload(path, legacy.to_dict())

    repository = HistoricalMatchRepository(path)
    loaded = repository.list_all()

    assert len(loaded) == 1
    assert loaded[0].match_context.official_match_id == "700000000"
    assert loaded[0].match_context.match_date == "2026-06-01"


def test_legacy_snapshot_gets_a_derived_status_without_crashing(tmp_path):
    path = tmp_path / "snapshots.json"
    legacy = HistoricalMatchSnapshot(
        snapshot_id="legacy1",
        match_context=MatchContext(match_date="2026-06-01"),
    )
    _write_legacy_payload(path, legacy.to_dict())

    repository = HistoricalMatchRepository(path)
    loaded = repository.list_all()[0]

    assert loaded.status in set(MatchRecordStatus)


def test_legacy_snapshot_season_week_defaults_to_unknown(tmp_path):
    path = tmp_path / "snapshots.json"
    legacy = HistoricalMatchSnapshot(snapshot_id="legacy1", match_context=MatchContext())
    _write_legacy_payload(path, legacy.to_dict())

    repository = HistoricalMatchRepository(path)
    loaded = repository.list_all()[0]

    assert loaded.season_week.is_known is False


def test_legacy_snapshot_with_existing_official_pre_and_post_migrates_intact(tmp_path):
    from engine.history.official_ratings.models import OfficialRatingSnapshot

    path = tmp_path / "snapshots.json"
    legacy = HistoricalMatchSnapshot(
        snapshot_id="legacy1",
        match_context=MatchContext(match_date="2026-06-01", official_match_id="700000000"),
        official_pre=OfficialRatingSnapshot(team_name="Hit em up"),
        official_post=OfficialRatingSnapshot(team_name="Hit em up"),
    )
    _write_legacy_payload(path, legacy.to_dict())

    repository = HistoricalMatchRepository(path)
    loaded = repository.list_all()[0]

    assert loaded.official_pre is not None
    assert loaded.official_post is not None
    assert loaded.status == MatchRecordStatus.COMPLETE


def test_legacy_snapshot_can_be_saved_again_after_loading(tmp_path):
    path = tmp_path / "snapshots.json"
    legacy = HistoricalMatchSnapshot(
        snapshot_id="legacy1",
        match_context=MatchContext(match_date="2026-06-01", official_match_id="700000000"),
    )
    _write_legacy_payload(path, legacy.to_dict())

    repository = HistoricalMatchRepository(path)
    loaded = repository.list_all()[0]
    repository.save(loaded.with_updates(ht_season_number=95, ht_season_week=1))

    reloaded = repository.get("legacy1")
    assert reloaded.ht_season_number == 95
    assert reloaded.match_context.official_match_id == "700000000"
