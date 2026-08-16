from datetime import date

import pytest

from engine.history.match_deletion import (
    delete_saved_match,
    find_linked_weekly_match_records,
)
from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    complete_with_official_post,
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from engine.weekly_training.models import CompetitionType, MatchRole, WeeklyMatchRecord
from engine.weekly_training.persistence import WeeklyTrainingRepository, WeeklyTrainingState


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


@pytest.fixture()
def weekly_repository(tmp_path):
    return WeeklyTrainingRepository(tmp_path / "planner.json")


def _weekly_match(match_date=date(2026, 8, 9), opponent="CA Chaco"):
    return WeeklyMatchRecord(
        match_id="w1", match_date=match_date, match_role=MatchRole.FIRST_WEEKLY_MATCH,
        opponent_name=opponent, competition_type=CompetitionType.LEAGUE, formation="3-5-2",
    )


def test_delete_removes_the_canonical_record(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    delete_saved_match(repository, record.snapshot_id)
    assert repository.get(record.snapshot_id) is None


def test_delete_removes_pre_post_and_retrospective_together_no_orphans(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    consolidated = consolidate_with_official_pre(
        repository, record, OfficialRatingSnapshot(), "770918226"
    )
    complete_with_official_post(repository, consolidated, OfficialRatingSnapshot(), "770918226")

    delete_saved_match(repository, record.snapshot_id)

    assert repository.list_all() == ()


def test_find_linked_weekly_match_records_matches_by_opponent_and_date():
    weekly_state = WeeklyTrainingState(match_records=(_weekly_match(),))
    historical_record = HistoricalMatchSnapshot(
        snapshot_id="s1",
        match_context=MatchContext(
            match_date="2026-08-09", opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
    )
    linked = find_linked_weekly_match_records(weekly_state, historical_record)
    assert len(linked) == 1
    assert linked[0].match_id == "w1"


def test_find_linked_weekly_match_records_none_when_opponent_differs():
    weekly_state = WeeklyTrainingState(match_records=(_weekly_match(opponent="Torres FC"),))
    historical_record = HistoricalMatchSnapshot(
        snapshot_id="s1",
        match_context=MatchContext(
            match_date="2026-08-09", opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
    )
    assert find_linked_weekly_match_records(weekly_state, historical_record) == ()


def test_delete_analysis_only_preserves_weekly_record(repository, weekly_repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    weekly_state = WeeklyTrainingState(match_records=(_weekly_match(),))
    weekly_repository.save(weekly_state)

    delete_saved_match(
        repository, record.snapshot_id, delete_weekly_link=False,
        weekly_repository=weekly_repository, weekly_state=weekly_state,
    )

    assert repository.get(record.snapshot_id) is None
    assert len(weekly_repository.load().match_records) == 1


def test_delete_analysis_and_weekly_removes_both(repository, weekly_repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    weekly_state = WeeklyTrainingState(match_records=(_weekly_match(),))
    weekly_repository.save(weekly_state)

    delete_saved_match(
        repository, record.snapshot_id, delete_weekly_link=True,
        weekly_repository=weekly_repository, weekly_state=weekly_state,
    )

    assert repository.get(record.snapshot_id) is None
    assert len(weekly_repository.load().match_records) == 0


def test_delete_never_touches_unrelated_weekly_records(repository, weekly_repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    other_weekly = WeeklyMatchRecord(
        match_id="w2", match_date=date(2026, 8, 16), match_role=MatchRole.SECOND_WEEKLY_MATCH,
        opponent_name="Torres FC", competition_type=CompetitionType.LEAGUE, formation="4-4-2",
    )
    weekly_state = WeeklyTrainingState(match_records=(_weekly_match(), other_weekly))
    weekly_repository.save(weekly_state)

    delete_saved_match(
        repository, record.snapshot_id, delete_weekly_link=True,
        weekly_repository=weekly_repository, weekly_state=weekly_state,
    )

    remaining = weekly_repository.load().match_records
    assert len(remaining) == 1
    assert remaining[0].match_id == "w2"


def test_delete_without_weekly_link_does_not_touch_weekly_state(repository, weekly_repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="Isolated Rival", match_date="2026-09-01", competition_type="friendly"
    )
    weekly_state = WeeklyTrainingState(match_records=(_weekly_match(),))
    weekly_repository.save(weekly_state)

    delete_saved_match(
        repository, record.snapshot_id, delete_weekly_link=True,
        weekly_repository=weekly_repository, weekly_state=weekly_state,
    )

    assert len(weekly_repository.load().match_records) == 1


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
    QApplication.instance() or QApplication([])


def _make_controller(tmp_path):
    from ht_coach_app.controllers.saved_matches_controller import SavedMatchesController
    from ht_coach_app.views.saved_matches_page import SavedMatchesPage

    hist_repo = HistoricalMatchRepository(tmp_path / "s.json")
    weekly_repo = WeeklyTrainingRepository(tmp_path / "p.json")
    page = SavedMatchesPage()
    controller = SavedMatchesController(page, hist_repo, weekly_repo)
    return page, controller, hist_repo, weekly_repo


def test_controller_delete_cancelled_deletes_nothing(tmp_path):
    page, controller, hist_repo, weekly_repo = _make_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    page.confirm_delete = lambda: False

    controller._delete_record(record.snapshot_id)

    assert hist_repo.get(record.snapshot_id) is not None


def test_controller_delete_confirmed_no_weekly_link(tmp_path):
    page, controller, hist_repo, weekly_repo = _make_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Isolated Rival", match_date="2026-09-01", competition_type="friendly"
    )
    page.confirm_delete = lambda: True

    controller._delete_record(record.snapshot_id)

    assert hist_repo.get(record.snapshot_id) is None


def test_controller_delete_confirmed_with_weekly_link_asks_second_dialog(tmp_path):
    page, controller, hist_repo, weekly_repo = _make_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    weekly_repo.save(WeeklyTrainingState(match_records=(_weekly_match(),)))

    page.confirm_delete = lambda: True
    calls = []
    page.confirm_weekly_link_deletion = lambda: calls.append(True) or "analysis_only"

    controller._delete_record(record.snapshot_id)

    assert calls == [True]
    assert hist_repo.get(record.snapshot_id) is None
    assert len(weekly_repo.load().match_records) == 1


def test_controller_delete_weekly_link_cancel_deletes_nothing(tmp_path):
    page, controller, hist_repo, weekly_repo = _make_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    weekly_repo.save(WeeklyTrainingState(match_records=(_weekly_match(),)))

    page.confirm_delete = lambda: True
    page.confirm_weekly_link_deletion = lambda: "cancel"

    controller._delete_record(record.snapshot_id)

    assert hist_repo.get(record.snapshot_id) is not None


def test_controller_delete_analysis_and_weekly_removes_both(tmp_path):
    page, controller, hist_repo, weekly_repo = _make_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    weekly_repo.save(WeeklyTrainingState(match_records=(_weekly_match(),)))

    page.confirm_delete = lambda: True
    page.confirm_weekly_link_deletion = lambda: "analysis_and_weekly"

    controller._delete_record(record.snapshot_id)

    assert hist_repo.get(record.snapshot_id) is None
    assert len(weekly_repo.load().match_records) == 0
