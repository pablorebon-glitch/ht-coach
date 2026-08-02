import pytest

from engine.history.duplicate_reconciliation import (
    find_duplicate_groups,
    merge_duplicate_group,
    reconcile_duplicates,
)
from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def _chaco_duplicate_fixture(repository):
    richer_in_evidence = HistoricalMatchSnapshot(
        snapshot_id="chaco-a", created_at="2026-08-01T10:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        official_post=OfficialRatingSnapshot(team_name="Hit em up"),
    )
    richer_in_metadata = HistoricalMatchSnapshot(
        snapshot_id="chaco-b", created_at="2026-08-01T09:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        ht_season_number=95, ht_season_week=2,
    )
    repository.save(richer_in_evidence)
    repository.save(richer_in_metadata)
    return richer_in_evidence, richer_in_metadata


def test_no_duplicates_when_records_are_genuinely_distinct(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-16",
        competition_type="league", season_number=95, season_week=3,
    )
    assert find_duplicate_groups(repository) == ()


def test_chaco_style_duplicate_is_detected_by_shared_match_id(repository):
    _chaco_duplicate_fixture(repository)
    groups = find_duplicate_groups(repository)
    assert len(groups) == 1
    assert groups[0].kind == "official_match_id"
    assert len(groups[0].records) == 2


def test_chaco_style_duplicate_is_safely_auto_mergeable(repository):
    _chaco_duplicate_fixture(repository)
    groups = find_duplicate_groups(repository)
    assert groups[0].can_auto_merge is True


def test_chaco_style_duplicate_repaired_end_to_end(repository):
    _chaco_duplicate_fixture(repository)

    report = reconcile_duplicates(repository)

    assert report.merged_count == 1
    assert report.unresolved_count == 0
    remaining = repository.list_all()
    assert len(remaining) == 1

    survivor = remaining[0]
    assert survivor.snapshot_id == "chaco-b"
    assert survivor.official_post is not None
    assert survivor.ht_season_number == 95
    assert survivor.match_context.official_match_id == "770918226"


def test_no_data_loss_across_the_merge(repository):
    richer_in_evidence, richer_in_metadata = _chaco_duplicate_fixture(repository)
    merged = merge_duplicate_group(
        repository, find_duplicate_groups(repository)[0]
    )
    assert merged.official_post is not None
    assert merged.ht_season_number == richer_in_metadata.ht_season_number
    assert merged.match_context.official_match_id == richer_in_evidence.match_context.official_match_id


def test_conflicting_official_post_is_never_auto_merged(repository):
    record_a = HistoricalMatchSnapshot(
        snapshot_id="a",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        official_post=OfficialRatingSnapshot(team_name="Team A"),
    )
    record_b = HistoricalMatchSnapshot(
        snapshot_id="b",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        official_post=OfficialRatingSnapshot(team_name="Team B"),
    )
    repository.save(record_a)
    repository.save(record_b)

    groups = find_duplicate_groups(repository)
    assert groups[0].can_auto_merge is False
    assert groups[0].conflict_reason == "multiple_official_post"


def test_conflicting_group_left_unresolved_not_silently_merged(repository):
    record_a = HistoricalMatchSnapshot(
        snapshot_id="a",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        official_pre=OfficialRatingSnapshot(team_name="A"),
    )
    record_b = HistoricalMatchSnapshot(
        snapshot_id="b",
        match_context=MatchContext(
            match_date="2026-08-09", official_match_id="770918226",
            opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        official_pre=OfficialRatingSnapshot(team_name="B"),
    )
    repository.save(record_a)
    repository.save(record_b)

    report = reconcile_duplicates(repository)

    assert report.merged_count == 0
    assert report.unresolved_count == 1
    assert len(repository.list_all()) == 2


def test_merge_duplicate_group_raises_when_not_mergeable(repository):
    record_a = HistoricalMatchSnapshot(
        snapshot_id="a",
        match_context=MatchContext(official_match_id="1", opponent=OpponentReference(opponent_name="X")),
        official_post=OfficialRatingSnapshot(team_name="A"),
    )
    record_b = HistoricalMatchSnapshot(
        snapshot_id="b",
        match_context=MatchContext(official_match_id="1", opponent=OpponentReference(opponent_name="X")),
        official_post=OfficialRatingSnapshot(team_name="B"),
    )
    repository.save(record_a)
    repository.save(record_b)

    group = find_duplicate_groups(repository)[0]
    with pytest.raises(ValueError):
        merge_duplicate_group(repository, group)


def test_opponent_week_evidence_grouping_for_records_without_match_id(repository):
    r1 = HistoricalMatchSnapshot(
        snapshot_id="p1", created_at="2026-08-01T09:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09", opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        ht_season_number=95, ht_season_week=2,
    )
    r2 = HistoricalMatchSnapshot(
        snapshot_id="p2", created_at="2026-08-01T10:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09", opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
        ht_season_number=95, ht_season_week=2,
    )
    repository.save(r1)
    repository.save(r2)

    groups = find_duplicate_groups(repository)
    assert len(groups) == 1
    assert groups[0].kind == "opponent_week_evidence"


def test_records_without_official_match_id_and_without_opponent_are_never_grouped(repository):
    r1 = HistoricalMatchSnapshot(snapshot_id="a", match_context=MatchContext())
    r2 = HistoricalMatchSnapshot(snapshot_id="b", match_context=MatchContext())
    repository.save(r1)
    repository.save(r2)
    assert find_duplicate_groups(repository) == ()


def test_report_never_silently_drops_ambiguous_groups(repository):
    _chaco_duplicate_fixture(repository)
    record_a = HistoricalMatchSnapshot(
        snapshot_id="conflict-a",
        match_context=MatchContext(
            official_match_id="999", opponent=OpponentReference(opponent_name="Rival X"),
        ),
        official_pre=OfficialRatingSnapshot(team_name="A"),
    )
    record_b = HistoricalMatchSnapshot(
        snapshot_id="conflict-b",
        match_context=MatchContext(
            official_match_id="999", opponent=OpponentReference(opponent_name="Rival X"),
        ),
        official_pre=OfficialRatingSnapshot(team_name="B"),
    )
    repository.save(record_a)
    repository.save(record_b)

    report = reconcile_duplicates(repository)

    assert report.merged_count == 1
    assert report.unresolved_count == 1


def test_home_and_away_leg_same_opponent_same_week_never_grouped_as_duplicate(repository):
    """Alpha 0.6.7 HF-02, Part 9: venue is part of the identity check
    for the weaker (no Match ID yet) signal -- a two-leg cup tie
    against the same opponent in the same week must never be
    mistaken for a duplicated record just because everything else
    matches."""
    home_leg = HistoricalMatchSnapshot(
        snapshot_id="leg-home",
        match_context=MatchContext(
            match_date="2026-08-09",
            opponent=OpponentReference(opponent_name="CA Chaco"),
            home_away="home",
        ),
        ht_season_number=95, ht_season_week=2,
    )
    away_leg = HistoricalMatchSnapshot(
        snapshot_id="leg-away",
        match_context=MatchContext(
            match_date="2026-08-09",
            opponent=OpponentReference(opponent_name="CA Chaco"),
            home_away="away",
        ),
        ht_season_number=95, ht_season_week=2,
    )
    repository.save(home_leg)
    repository.save(away_leg)

    assert find_duplicate_groups(repository) == ()


def test_same_venue_still_correctly_detected_as_duplicate(repository):
    r1 = HistoricalMatchSnapshot(
        snapshot_id="p1", created_at="2026-08-01T09:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09",
            opponent=OpponentReference(opponent_name="CA Chaco"),
            home_away="home",
        ),
        ht_season_number=95, ht_season_week=2,
    )
    r2 = HistoricalMatchSnapshot(
        snapshot_id="p2", created_at="2026-08-01T10:00:00Z",
        match_context=MatchContext(
            match_date="2026-08-09",
            opponent=OpponentReference(opponent_name="CA Chaco"),
            home_away="home",
        ),
        ht_season_number=95, ht_season_week=2,
    )
    repository.save(r1)
    repository.save(r2)

    groups = find_duplicate_groups(repository)
    assert len(groups) == 1
    assert groups[0].kind == "opponent_week_evidence"
