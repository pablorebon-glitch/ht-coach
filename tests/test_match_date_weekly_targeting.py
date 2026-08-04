import pytest

from datetime import date

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.repository import HistoricalMatchRepository
from engine.weekly_training.persistence import WeeklyTrainingRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    TeamRatingsResult,
)
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.views.match_page import MatchPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _lineup():
    return [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order="Normal", order_side="", player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]


def _result(opponent="CA Chaco", match_type="LEAGUE"):
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=_lineup(),
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name=opponent,
        formations=[formation],
        match_type=match_type,
    )


def make_controller(tmp_path):
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    weekly_service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    official_service = OfficialRatingImportService(repository=hist_repo)
    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo,
        weekly_training_service=weekly_service,
        official_rating_service=official_service,
    )
    page.set_match_type("LEAGUE")
    return page, controller, weekly_service


def test_saved_record_reflects_the_selected_historical_date(tmp_path):
    page, controller, weekly_service = make_controller(tmp_path)
    page.set_match_date("2026-07-26")
    controller._settings_repository.save_last_result(_result())

    controller._save_as_first_match()

    state = weekly_service.load_state()
    saved = [r for r in state.match_records if r.match_role.value == "FIRST_WEEKLY_MATCH"]
    assert len(saved) == 1
    assert saved[0].match_date.isoformat() == "2026-07-26"


def test_replace_confirmation_dialog_names_the_actually_affected_week(tmp_path):
    page, controller, weekly_service = make_controller(tmp_path)
    controller._settings_repository.save_last_result(_result())
    controller._save_as_first_match()

    calls = []
    page.confirm_replace_first_match = lambda start, end: calls.append((start, end)) or False
    controller._save_as_first_match()

    assert len(calls) == 1
    start, end = calls[0]
    assert start and end
    assert "/" in start and "/" in end


def test_dialog_week_range_matches_the_record_actually_being_replaced(tmp_path):
    from datetime import datetime

    page, controller, weekly_service = make_controller(tmp_path)
    controller._settings_repository.save_last_result(_result())
    controller._save_as_first_match()

    state = weekly_service.load_state()
    existing = next(r for r in state.match_records if r.match_role.value == "FIRST_WEEKLY_MATCH")
    week_start_from_id = existing.match_id.split(":")[0]

    week_start, week_end = controller._target_week_range()
    assert datetime.strptime(week_start, "%d/%m/%Y").date().isoformat() == week_start_from_id


def test_historical_match_id_now_derives_from_its_own_date(tmp_path):
    """Alpha 0.6.7 HF-02, Part 3 -- the real fix, not the earlier
    scoped-down version. A historical match_date now determines its
    own training-cycle identity (match_id), not just its display
    field. Verified this never regresses the "current week" case
    elsewhere in tests/test_weekly_training_planner.py, which controls
    for the real, deterministic derivation instead of the active-week
    shortcut this used to rely on."""
    page, controller, weekly_service = make_controller(tmp_path)
    page.set_match_date("2026-07-26")
    controller._settings_repository.save_last_result(_result())
    controller._save_as_first_match()

    state = weekly_service.load_state()
    saved = next(r for r in state.match_records if r.match_role.value == "FIRST_WEEKLY_MATCH")
    assert saved.match_id == "2026-07-26:PLAYMAKING:first"


def test_second_match_date_also_correctly_preserved(tmp_path):
    page, controller, weekly_service = make_controller(tmp_path)
    page.set_match_date("2026-07-23")
    controller._settings_repository.save_last_result(_result())
    page.confirm_save_match_type_mismatch = lambda *args: True

    controller._save_as_second_match()

    state = weekly_service.load_state()
    saved = [r for r in state.match_records if r.match_role.value == "SECOND_WEEKLY_MATCH"]
    assert len(saved) == 1
    assert saved[0].match_date.isoformat() == "2026-07-23"


def test_todays_default_date_always_matches_active_week_even_across_rollover(tmp_path):
    """Alpha 0.6.7 HF-02, Part 3: a real edge case found while fixing
    this properly. `active_week.end_date` marks the Thursday
    training-update cutoff, not the calendar week's end -- so "today"
    can genuinely fall *before* `active_week.start_date` (e.g. a
    Saturday, after Thursday's rollover already advanced the active
    week to the following Sunday). The week-identity derivation must
    still agree with `active_week.week_id` in this case, since nothing
    about the date was ever deliberately changed by the user -- it's
    still just "today's default"."""
    from engine.weekly_training.persistence import WeeklyTrainingRepository
    from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService

    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    state = service.load_state()
    resolved = service._week_id_for_target_date(
        state.active_week, date.today(), state.active_training_type
    )
    assert resolved == state.active_week.week_id
