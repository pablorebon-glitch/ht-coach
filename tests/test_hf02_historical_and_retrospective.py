"""Alpha 0.6.7 HF-02, Parts 17-18: historical match creation and
retrospective PRE Match ID rules, verified against this hotfix's own
scenarios rather than only re-running pre-existing tests from the
sprint that originally built these mechanisms.
"""
from datetime import date, timedelta

import pytest

from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    complete_with_official_post,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from engine.history.retrospective_pre import detect_retrospective_pre_candidate


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def _past_date(days_ago=10):
    return (date.today() - timedelta(days=days_ago)).isoformat()


def test_part17_historical_match_created_with_opponent_type_venue_old_date(repository):
    past = _past_date()
    record = find_or_create_provisional_record(
        repository, opponent_name="Rival Histórico", match_date=past,
        competition_type="cup", home_away="away",
    )
    assert record.match_context.opponent.opponent_name == "Rival Histórico"
    assert record.match_context.competition_type.value == "cup"
    assert record.match_context.home_away.value == "away"
    assert record.match_context.match_date == past


def test_part17_official_post_may_be_imported_without_pre(repository):
    past = _past_date()
    record = find_or_create_provisional_record(
        repository, opponent_name="Rival Histórico", match_date=past, competition_type="league"
    )
    record = complete_with_official_post(
        repository, record, OfficialRatingSnapshot(team_name="Equipo"), "888777666"
    )
    assert record.official_pre is None
    assert record.official_post is not None


def test_part17_never_fabricates_a_pre_for_a_historical_match(repository):
    past = _past_date()
    record = find_or_create_provisional_record(
        repository, opponent_name="Rival Histórico", match_date=past, competition_type="league"
    )
    record = complete_with_official_post(
        repository, record, OfficialRatingSnapshot(), "1"
    )
    reloaded = repository.get(record.snapshot_id)
    assert reloaded.official_pre is None


def test_part18_different_match_id_offers_retrospective_candidate(repository):
    past = _past_date()
    record = find_or_create_provisional_record(
        repository, opponent_name="Rival Histórico", match_date=past, competition_type="league"
    )
    record = complete_with_official_post(
        repository, record, OfficialRatingSnapshot(team_name="Equipo"), "888777666"
    )

    parsed = type("Parsed", (), {"hattrick_match_id": "999999999"})()
    candidate = detect_retrospective_pre_candidate(repository, parsed)

    assert candidate is not None
    assert candidate.snapshot_id == record.snapshot_id


def test_part18_matching_official_match_id_never_goes_through_retrospective(repository):
    past = _past_date()
    record = find_or_create_provisional_record(
        repository, opponent_name="Rival Histórico", match_date=past, competition_type="league"
    )
    complete_with_official_post(
        repository, record, OfficialRatingSnapshot(team_name="Equipo"), "888777666"
    )

    parsed = type("Parsed", (), {"hattrick_match_id": "888777666"})()
    candidate = detect_retrospective_pre_candidate(repository, parsed)

    assert candidate is None


def test_part18_no_match_id_in_pasted_text_is_never_a_retrospective_candidate(repository):
    past = _past_date()
    record = find_or_create_provisional_record(
        repository, opponent_name="Rival Histórico", match_date=past, competition_type="league"
    )
    complete_with_official_post(repository, record, OfficialRatingSnapshot(), "1")

    parsed = type("Parsed", (), {"hattrick_match_id": ""})()
    candidate = detect_retrospective_pre_candidate(repository, parsed)

    assert candidate is None
