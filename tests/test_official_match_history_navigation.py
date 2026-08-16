import pytest

from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.record_navigation import (
    available_seasons,
    list_records,
    navigate_records,
)
from engine.history.repository import HistoricalMatchRepository


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def _seed(repository):
    from datetime import date, timedelta

    today = date.today()
    future_1 = (today + timedelta(days=9)).isoformat()
    future_2 = (today + timedelta(days=2)).isoformat()
    past = (today - timedelta(days=11)).isoformat()

    r1 = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date=future_1,
        competition_type="league", season_number=95, season_week=2,
    )
    r2 = find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date=future_2,
        competition_type="league", season_number=95, season_week=1,
    )
    r3 = find_or_create_provisional_record(
        repository, opponent_name="Boca Deportivo", match_date=past,
        competition_type="cup", season_number=94, season_week=16,
    )
    return r1, r2, r3


def test_available_seasons_lists_distinct_seasons_descending(repository):
    _seed(repository)
    assert available_seasons(repository) == (95, 94)


def test_available_seasons_excludes_unknown_season(repository):
    find_or_create_provisional_record(
        repository, opponent_name="Unknown Rival", match_date="2026-08-09",
        competition_type="league", season_number=None, season_week=None,
    )
    assert available_seasons(repository) == ()


def test_list_records_sorted_most_recent_first(repository):
    _seed(repository)
    records = list_records(repository)
    dates = [r.match_context.match_date for r in records]
    assert dates == sorted(dates, reverse=True)


def test_list_records_filters_by_season(repository):
    _seed(repository)
    records = list_records(repository, season_number=95)
    assert len(records) == 2
    assert all(r.ht_season_number == 95 for r in records)


def test_list_records_filters_by_competition_type(repository):
    _seed(repository)
    records = list_records(repository, competition_type="cup")
    assert len(records) == 1
    assert records[0].match_context.opponent.opponent_name == "Boca Deportivo"


def test_list_records_filters_by_status(repository):
    from engine.history.enums import MatchRecordStatus

    _seed(repository)
    # Only the two future-dated matches count as PLANNED; the third
    # seeded record's date (2026-07-20) is in the past relative to the
    # real "today" and has no PRE/POST evidence, so it's INCOMPLETE.
    planned = list_records(repository, status=MatchRecordStatus.PLANNED)
    assert len(planned) == 2
    incomplete = list_records(repository, status=MatchRecordStatus.INCOMPLETE)
    assert len(incomplete) == 1


def test_navigate_records_defaults_to_first_when_no_current_given(repository):
    _seed(repository)
    records = list_records(repository)
    ctx = navigate_records(records)
    assert ctx.record.snapshot_id == records[0].snapshot_id
    assert ctx.total == 3


def test_navigate_next_moves_to_a_chronologically_newer_record(repository):
    _seed(repository)
    records = list_records(repository, season_number=95)
    # start at the oldest of the two season-95 records
    start = navigate_records(records, current_snapshot_id=records[-1].snapshot_id, direction="current")
    moved = navigate_records(records, current_snapshot_id=start.record.snapshot_id, direction="next")
    assert moved.record.match_context.match_date > start.record.match_context.match_date


def test_navigate_previous_moves_to_a_chronologically_older_record(repository):
    _seed(repository)
    records = list_records(repository, season_number=95)
    # start at the newest of the two season-95 records
    start = navigate_records(records, current_snapshot_id=records[0].snapshot_id, direction="current")
    moved = navigate_records(records, current_snapshot_id=start.record.snapshot_id, direction="previous")
    assert moved.record.match_context.match_date < start.record.match_context.match_date


def test_navigate_previous_from_the_oldest_record_stays_there(repository):
    """There is nothing chronologically older than the oldest record --
    "previous" from it must not move (and must disable itself)."""
    _seed(repository)
    records = list_records(repository, season_number=95)
    oldest = records[-1]
    ctx = navigate_records(records, current_snapshot_id=oldest.snapshot_id, direction="previous")
    assert ctx.record.snapshot_id == oldest.snapshot_id
    assert ctx.can_go_previous is False


def test_navigate_next_from_the_newest_record_stays_there(repository):
    """There is nothing chronologically newer than the newest record --
    "next" from it must not move (and must disable itself)."""
    _seed(repository)
    records = list_records(repository, season_number=95)
    newest = records[0]
    ctx = navigate_records(records, current_snapshot_id=newest.snapshot_id, direction="next")
    assert ctx.record.snapshot_id == newest.snapshot_id
    assert ctx.can_go_next is False


def test_navigate_empty_records_is_safe(repository):
    ctx = navigate_records([])
    assert ctx.record is None
    assert ctx.total == 0
    assert ctx.can_go_previous is False
    assert ctx.can_go_next is False


def test_navigation_never_crosses_active_filter_boundary(repository):
    _seed(repository)
    records = list_records(repository, season_number=95)
    ctx = navigate_records(records, current_snapshot_id=records[0].snapshot_id, direction="next")
    assert ctx.record.ht_season_number == 95
