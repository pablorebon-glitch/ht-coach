import pytest

from engine.history.match_lookup import find_existing_or_conflicting_record
from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def test_no_existing_records_returns_none(repository):
    result = find_existing_or_conflicting_record(
        repository, "CA Chaco", "league", "2026-08-09", 95, 2
    )
    assert result.kind == "none"
    assert result.record is None


def test_exact_same_match_is_detected(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    result = find_existing_or_conflicting_record(
        repository, "CA Chaco", "league", "2026-08-09", 95, 2
    )
    assert result.kind == "exact"
    assert result.record.match_context.opponent.opponent_name == "CA Chaco"


def test_exact_match_is_case_insensitive_on_opponent_name(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    result = find_existing_or_conflicting_record(
        repository, "ca chaco", "league", "2026-08-09", 95, 2
    )
    assert result.kind == "exact"


def test_different_opponent_never_conflicts(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    result = find_existing_or_conflicting_record(
        repository, "Torres FC", "league", "2026-08-09", 95, 2
    )
    assert result.kind == "none"


def test_same_opponent_same_competition_different_date_is_a_new_match(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    result = find_existing_or_conflicting_record(
        repository, "CA Chaco", "league", "2026-09-06", 95, 6
    )
    assert result.kind == "none"


def test_briefs_own_example_conflict_liga_vs_copa_same_week(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="cup", season_number=95, season_week=2,
    )
    result = find_existing_or_conflicting_record(
        repository, "CA Chaco", "league", "2026-08-09", 95, 2
    )
    assert result.kind == "conflict"
    assert result.record.match_context.opponent.opponent_name == "CA Chaco"


def test_conflict_detected_by_same_ht_week_even_with_different_exact_date(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-08",
        competition_type="cup", season_number=95, season_week=2,
    )
    result = find_existing_or_conflicting_record(
        repository, "CA Chaco", "league", "2026-08-09", 95, 2
    )
    assert result.kind == "conflict"


def test_conflict_never_raised_for_the_same_competition_type(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    result = find_existing_or_conflicting_record(
        repository, "CA Chaco", "league", "2026-08-16", 95, 2
    )
    assert result.kind != "conflict"


def test_exact_match_takes_priority_over_conflict_detection(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    result = find_existing_or_conflicting_record(
        repository, "CA Chaco", "league", "2026-08-09", 95, 2
    )
    assert result.kind == "exact"
