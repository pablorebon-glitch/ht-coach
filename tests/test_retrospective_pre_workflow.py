import pytest

from engine.history.enums import MatchRecordStatus
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    complete_with_official_post,
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from engine.history.retrospective_pre import (
    detect_retrospective_pre_candidate,
    save_as_retrospective_simulation,
)


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def _played_record_missing_pre(repository, match_id="770918226"):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-07-20",
        competition_type="league", season_number=95, season_week=1,
    )
    post = OfficialRatingSnapshot(team_name="Hit em up")
    return complete_with_official_post(repository, record, post, match_id)


def test_detects_candidate_for_reproduced_formation_with_different_match_id(repository):
    _played_record_missing_pre(repository)
    reproduced = OfficialRatingSnapshot(team_name="Hit em up", hattrick_match_id="771000000")

    candidate = detect_retrospective_pre_candidate(repository, reproduced)

    assert candidate is not None
    assert candidate.match_context.opponent.opponent_name == "CA Chaco"


def test_no_candidate_when_match_id_already_known(repository):
    record = _played_record_missing_pre(repository, match_id="770918226")
    same_match_pre = OfficialRatingSnapshot(hattrick_match_id="770918226")

    candidate = detect_retrospective_pre_candidate(repository, same_match_pre)

    assert candidate is None


def test_no_candidate_when_no_match_id_in_parsed_text(repository):
    _played_record_missing_pre(repository)
    no_id = OfficialRatingSnapshot(hattrick_match_id="")
    assert detect_retrospective_pre_candidate(repository, no_id) is None


def test_no_candidate_when_nothing_is_missing_pre(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    consolidate_with_official_pre(
        repository, record, OfficialRatingSnapshot(), "770100000"
    )
    reproduced = OfficialRatingSnapshot(hattrick_match_id="771000000")
    assert detect_retrospective_pre_candidate(repository, reproduced) is None


def test_no_candidate_for_still_planned_future_matches(repository):
    from datetime import date, timedelta

    future = (date.today() + timedelta(days=7)).isoformat()
    find_or_create_provisional_record(
        repository, opponent_name="Future Rival", match_date=future,
        competition_type="league", season_number=95, season_week=3,
    )
    reproduced = OfficialRatingSnapshot(hattrick_match_id="771000000")
    assert detect_retrospective_pre_candidate(repository, reproduced) is None


def test_save_as_retrospective_never_overwrites_official_match_id(repository):
    completed = _played_record_missing_pre(repository, match_id="770918226")
    reproduced = OfficialRatingSnapshot(hattrick_match_id="771000000")

    saved = save_as_retrospective_simulation(repository, completed, reproduced)

    assert saved.match_context.official_match_id == "770918226"


def test_save_as_retrospective_stores_source_and_linked_match_ids(repository):
    completed = _played_record_missing_pre(repository, match_id="770918226")
    reproduced = OfficialRatingSnapshot(hattrick_match_id="771000000")

    saved = save_as_retrospective_simulation(repository, completed, reproduced)

    assert saved.retrospective_pre.source_match_id == "771000000"
    assert saved.retrospective_pre.linked_match_id == "770918226"
    assert saved.retrospective_pre.captured_after_match is True


def test_save_as_retrospective_never_creates_a_new_record(repository):
    completed = _played_record_missing_pre(repository)
    reproduced = OfficialRatingSnapshot(hattrick_match_id="771000000")

    save_as_retrospective_simulation(repository, completed, reproduced)

    assert len(repository.list_all()) == 1


def test_save_as_retrospective_updates_status(repository):
    completed = _played_record_missing_pre(repository)
    reproduced = OfficialRatingSnapshot(hattrick_match_id="771000000")

    saved = save_as_retrospective_simulation(repository, completed, reproduced)

    assert saved.status == MatchRecordStatus.RETROSPECTIVE_PRE_AVAILABLE


def test_save_as_retrospective_stores_confidence_and_limitation(repository):
    completed = _played_record_missing_pre(repository)
    reproduced = OfficialRatingSnapshot(hattrick_match_id="771000000")

    saved = save_as_retrospective_simulation(
        repository, completed, reproduced, confidence="low", limitation="Simulated after the match."
    )

    assert saved.retrospective_pre.confidence == "low"
    assert saved.retrospective_pre.limitation == "Simulated after the match."


def test_retrospective_never_labeled_as_official_source_type(repository):
    from engine.history.enums import OfficialRatingSourceType

    completed = _played_record_missing_pre(repository)
    reproduced = OfficialRatingSnapshot(hattrick_match_id="771000000")

    saved = save_as_retrospective_simulation(repository, completed, reproduced)

    assert saved.retrospective_pre.source_type == OfficialRatingSourceType.RETROSPECTIVE_PRE.value
    assert saved.retrospective_pre.source_type != OfficialRatingSourceType.OFFICIAL_PRE.value


def test_comparison_label_official_when_official_pre_present():
    from ht_coach_app.core.localization import configure_localization
    from ht_coach_app.services.retrospective_comparison_formatting import comparison_label

    configure_localization("es")
    assert comparison_label(True, False) == "PRE oficial vs. POST oficial"
    configure_localization("en")


def test_comparison_label_retrospective_when_only_retrospective_present():
    from ht_coach_app.core.localization import configure_localization
    from ht_coach_app.services.retrospective_comparison_formatting import comparison_label

    configure_localization("es")
    assert comparison_label(False, True) == "Simulación retrospectiva vs. POST oficial"
    configure_localization("en")


def test_comparison_label_never_says_official_pre_when_only_retrospective():
    from ht_coach_app.core.localization import configure_localization
    from ht_coach_app.services.retrospective_comparison_formatting import comparison_label

    configure_localization("es")
    label = comparison_label(False, True)
    assert "PRE oficial" not in label
    configure_localization("en")


def test_retrospective_limitation_text_is_visible_and_nonempty():
    from ht_coach_app.core.localization import configure_localization
    from ht_coach_app.services.retrospective_comparison_formatting import (
        retrospective_limitation_text,
    )

    configure_localization("es")
    text = retrospective_limitation_text()
    assert text
    assert "después del partido" in text
    configure_localization("en")
