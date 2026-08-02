import json

import pytest

from engine.history.migration import migrate_to_unified_workflow
from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    complete_with_official_post,
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def _write_legacy_payload(path, snapshot_dicts):
    for snapshot_dict in snapshot_dicts:
        for key in (
            "retrospective_pre", "provisional_identity", "training_cycle_id",
            "ht_season_number", "ht_season_week",
        ):
            snapshot_dict.pop(key, None)
    path.write_text(
        json.dumps({"schema_version": 1, "snapshots": snapshot_dicts}),
        encoding="utf-8",
    )


def test_migration_of_empty_repository_is_clean(repository):
    report = migrate_to_unified_workflow(repository)
    assert report.total_records_before == 0
    assert report.total_records_after == 0
    assert report.is_clean is True


def test_migration_preserves_normal_records_untouched(repository):
    find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    report = migrate_to_unified_workflow(repository)
    assert report.total_records_before == 1
    assert report.total_records_after == 1
    assert report.merged_duplicate_groups == 0
    assert report.is_clean is True


def test_migration_preserves_pre_post_retrospective_and_match_id(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    consolidated = consolidate_with_official_pre(
        repository, record, OfficialRatingSnapshot(team_name="Hit em up"), "770918226"
    )
    complete_with_official_post(
        repository, consolidated, OfficialRatingSnapshot(team_name="Hit em up"), "770918226"
    )

    migrate_to_unified_workflow(repository)

    survivor = repository.get(record.snapshot_id)
    assert survivor.official_pre is not None
    assert survivor.official_post is not None
    assert survivor.match_context.official_match_id == "770918226"


def test_migration_merges_chaco_style_duplicates(repository):
    chaco_a = HistoricalMatchSnapshot(
        snapshot_id="chaco-a", created_at="2026-08-01T10:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        official_post=OfficialRatingSnapshot(),
    )
    chaco_b = HistoricalMatchSnapshot(
        snapshot_id="chaco-b", created_at="2026-08-01T09:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        ht_season_number=95, ht_season_week=2,
    )
    repository.save(chaco_a)
    repository.save(chaco_b)

    report = migrate_to_unified_workflow(repository)

    assert report.total_records_before == 2
    assert report.total_records_after == 1
    assert report.merged_duplicate_groups == 1
    assert len(repository.list_all()) == 1


def test_migration_never_silently_discards_ambiguous_duplicates(repository):
    record_a = HistoricalMatchSnapshot(
        snapshot_id="a",
        match_context=MatchContext(
            official_match_id="999", opponent=OpponentReference(opponent_name="Rival X"),
        ),
        official_post=OfficialRatingSnapshot(team_name="A"),
    )
    record_b = HistoricalMatchSnapshot(
        snapshot_id="b",
        match_context=MatchContext(
            official_match_id="999", opponent=OpponentReference(opponent_name="Rival X"),
        ),
        official_post=OfficialRatingSnapshot(team_name="B"),
    )
    repository.save(record_a)
    repository.save(record_b)

    report = migrate_to_unified_workflow(repository)

    assert report.total_records_before == 2
    assert report.total_records_after == 2
    assert report.merged_duplicate_groups == 0
    assert len(report.unresolved_duplicate_groups) == 1
    assert report.is_clean is False


def test_migration_report_serializes_to_dict(repository):
    record_a = HistoricalMatchSnapshot(
        snapshot_id="a",
        match_context=MatchContext(
            official_match_id="1", opponent=OpponentReference(opponent_name="X"),
        ),
        official_post=OfficialRatingSnapshot(team_name="A"),
    )
    record_b = HistoricalMatchSnapshot(
        snapshot_id="b",
        match_context=MatchContext(
            official_match_id="1", opponent=OpponentReference(opponent_name="X"),
        ),
        official_post=OfficialRatingSnapshot(team_name="B"),
    )
    repository.save(record_a)
    repository.save(record_b)

    report = migrate_to_unified_workflow(repository)
    payload = report.to_dict()

    assert payload["total_records_before"] == 2
    assert len(payload["unresolved_duplicate_groups"]) == 1
    assert payload["unresolved_duplicate_groups"][0]["conflict_reason"] == "multiple_official_post"


def test_migration_finds_no_status_invariant_violations_in_healthy_data(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-09", competition_type="league"
    )
    consolidated = consolidate_with_official_pre(repository, record, OfficialRatingSnapshot(), "1")
    complete_with_official_post(repository, consolidated, OfficialRatingSnapshot(), "1")

    report = migrate_to_unified_workflow(repository)

    assert report.status_invariant_violations == ()


def test_migration_of_legacy_payload_without_new_fields(tmp_path):
    path = tmp_path / "snapshots.json"
    legacy = HistoricalMatchSnapshot(
        snapshot_id="legacy1",
        match_context=MatchContext(match_date="2026-06-01", official_match_id="700000000"),
    )
    _write_legacy_payload(path, [legacy.to_dict()])

    repository = HistoricalMatchRepository(path)
    report = migrate_to_unified_workflow(repository)

    assert report.total_records_before == 1
    assert report.total_records_after == 1
    assert report.is_clean is True
    survivor = repository.list_all()[0]
    assert survivor.match_context.official_match_id == "700000000"


def test_migration_of_mixed_legacy_and_duplicate_data(tmp_path):
    path = tmp_path / "snapshots.json"
    legacy = HistoricalMatchSnapshot(
        snapshot_id="legacy1",
        match_context=MatchContext(match_date="2026-06-01", official_match_id="700000000"),
    )
    chaco_a = HistoricalMatchSnapshot(
        snapshot_id="chaco-a", created_at="2026-08-01T10:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        official_post=OfficialRatingSnapshot(),
    )
    chaco_b = HistoricalMatchSnapshot(
        snapshot_id="chaco-b", created_at="2026-08-01T09:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        ht_season_number=95, ht_season_week=2,
    )
    _write_legacy_payload(path, [legacy.to_dict(), chaco_a.to_dict(), chaco_b.to_dict()])

    repository = HistoricalMatchRepository(path)
    assert len(repository.list_all()) == 3

    report = migrate_to_unified_workflow(repository)

    assert report.total_records_before == 3
    assert report.total_records_after == 2
    assert report.merged_duplicate_groups == 1
    assert report.is_clean is True
    assert len(repository.list_all()) == 2
