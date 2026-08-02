import pytest

from engine.history.enums import MatchRecordStatus
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    MatchIdMismatchError,
    complete_with_official_post,
    compute_provisional_identity,
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def test_provisional_identity_is_stable_and_deterministic():
    identity_a = compute_provisional_identity(95, 2, "2026-08-09", "CA Chaco", "league")
    identity_b = compute_provisional_identity(95, 2, "2026-08-09", "CA Chaco", "league")
    assert identity_a == identity_b


def test_provisional_identity_is_case_insensitive_for_opponent_name():
    identity_a = compute_provisional_identity(95, 2, "2026-08-09", "CA Chaco", "league")
    identity_b = compute_provisional_identity(95, 2, "2026-08-09", "ca chaco", "league")
    assert identity_a == identity_b


def test_provisional_identity_differs_for_different_opponents():
    identity_a = compute_provisional_identity(95, 2, "2026-08-09", "CA Chaco", "league")
    identity_b = compute_provisional_identity(95, 2, "2026-08-09", "Torres FC", "league")
    assert identity_a != identity_b


def test_find_or_create_provisional_record_creates_new(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    assert record.provisional_identity
    assert record.match_context.opponent.opponent_name == "CA Chaco"
    assert record.status == MatchRecordStatus.PLANNED


def test_saving_the_same_provisional_match_twice_does_not_duplicate(repository):
    first = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    second = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    assert first.snapshot_id == second.snapshot_id
    assert len(repository.list_all()) == 1


def test_different_matches_produce_different_provisional_records(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-16",
        competition_type="league", season_number=95, season_week=3,
    )
    assert len(repository.list_all()) == 2


def test_official_pre_consolidates_the_same_record_not_a_new_one(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    pre = OfficialRatingSnapshot(team_name="Hit em up")
    consolidated = consolidate_with_official_pre(repository, record, pre, "770918226")

    assert consolidated.snapshot_id == record.snapshot_id
    assert consolidated.match_context.official_match_id == "770918226"
    assert consolidated.official_pre is pre
    assert len(repository.list_all()) == 1


def test_consolidation_updates_status_to_pre_imported(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    pre = OfficialRatingSnapshot()
    consolidated = consolidate_with_official_pre(repository, record, pre, "770918226")
    assert consolidated.status == MatchRecordStatus.PRE_OFFICIAL_IMPORTED


def test_official_post_completes_the_same_record(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    pre = OfficialRatingSnapshot()
    consolidated = consolidate_with_official_pre(repository, record, pre, "770918226")
    post = OfficialRatingSnapshot()
    completed = complete_with_official_post(repository, consolidated, post, "770918226")

    assert completed.snapshot_id == record.snapshot_id
    assert completed.status == MatchRecordStatus.COMPLETE
    assert len(repository.list_all()) == 1


def test_post_with_mismatched_match_id_raises_without_overwriting(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    pre = OfficialRatingSnapshot()
    consolidated = consolidate_with_official_pre(repository, record, pre, "770918226")
    post = OfficialRatingSnapshot()

    with pytest.raises(MatchIdMismatchError):
        complete_with_official_post(repository, consolidated, post, "999999")

    stored = repository.get(record.snapshot_id)
    assert stored.official_post is None
    assert stored.match_context.official_match_id == "770918226"


def test_post_without_prior_pre_completes_using_post_match_id(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    post = OfficialRatingSnapshot()
    completed = complete_with_official_post(repository, record, post, "770918226")
    assert completed.official_post is post
    assert completed.status == MatchRecordStatus.INCOMPLETE


def test_full_progressive_flow_never_creates_more_than_one_record(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
        training_cycle_id="2026-08-02",
    )
    pre = OfficialRatingSnapshot()
    consolidated = consolidate_with_official_pre(repository, record, pre, "770918226")
    post = OfficialRatingSnapshot()
    complete_with_official_post(repository, consolidated, post, "770918226")

    assert len(repository.list_all()) == 1
    final = repository.get(record.snapshot_id)
    assert final.status == MatchRecordStatus.COMPLETE
    assert final.training_cycle_id == "2026-08-02"
    assert final.ht_season_number == 95


def test_provisional_identity_never_collides_via_bare_concatenation():
    """Alpha 0.6.7, Part 2: guards against exactly the collision risk
    the brief calls out -- "opponent 1 + competition 1" must never
    equal a different combination that happens to concatenate to the
    same digits. Our delimiter-based, named-field identity structurally
    prevents this."""
    id_a = compute_provisional_identity(1, None, "", "1", "1")
    id_b = compute_provisional_identity(11, None, "", "", "1")
    assert id_a != id_b


def test_provisional_identity_distinguishes_two_matches_same_opponent_different_competition():
    """Part 2's own example: two matches against the same opponent
    (e.g. one Liga, one Copa) must never collide into one identity."""
    league_id = compute_provisional_identity(95, 2, "2026-08-09", "CA Chaco", "league")
    cup_id = compute_provisional_identity(95, 2, "2026-08-09", "CA Chaco", "cup")
    assert league_id != cup_id
