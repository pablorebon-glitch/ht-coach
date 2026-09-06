import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from datetime import datetime

from engine.calendar import HTCalendarService
from engine.history.repository import HistoricalMatchRepository
from engine.weekly_training.persistence import WeeklyTrainingRepository, WeeklyTrainingState
from engine.weekly_training.models import TrainingPriority
from engine.weekly_training.training_week import active_training_week
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.controllers.squad_controller import SquadController
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
from ht_coach_app.services.squad_service import SquadService
from ht_coach_app.services.ht_week_context_provider import (
    get_calendar_service,
    set_calendar_service,
)
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.state.app_events import AppEvents
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.views.squad_page import SquadPage
from models.player import Player


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


def _analysis_result(match_type="LEAGUE"):
    formation = FormationAnalysisResult(
        formation_name="3-5-2", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(),
        lineup=_lineup(),
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name="Rival FC",
        formations=[formation],
        match_type=match_type,
    )


def _player(name="Michael Rushton"):
    return Player(
        name=name,
        age=23,
        days=12,
        speciality="",
        form=7,
        stamina=7,
        goalkeeper=1,
        defending=5,
        playmaking=8,
        winger=5,
        passing=5,
        scoring=5,
        set_pieces=4,
        experience=5,
        leadership=4,
        tsi=1200,
        salary=1000,
        injury=None,
    )


@pytest.fixture(autouse=True)
def _fixed_calendar_service():
    previous = get_calendar_service()
    fixed_now = datetime(2026, 8, 1, 12, 0, 0)
    set_calendar_service(HTCalendarService(clock=lambda: fixed_now))
    yield
    set_calendar_service(previous)


def make_match_controller(tmp_path, app_events):
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "match_settings.json",
        result_storage_path=tmp_path / "match_result.json",
    )
    weekly_repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_repository.save(
        WeeklyTrainingState(active_week=active_training_week(datetime(2026, 8, 1, 12, 0, 0)))
    )
    weekly_service = WeeklyTrainingAppService(repository=weekly_repository)
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    official_service = OfficialRatingImportService(repository=hist_repo)
    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo, app_events=app_events,
        weekly_training_service=weekly_service,
        official_rating_service=official_service,
    )
    page.set_match_type("LEAGUE")
    return page, controller, weekly_service


def make_squad_controller(tmp_path, app_events):
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "squad_settings.json",
        result_storage_path=tmp_path / "squad_result.json",
    )
    page = SquadPage()
    controller = SquadController(page, SquadService(), settings_repo, app_events)
    return page, controller


def test_saving_first_match_emits_weekly_plan_saved(tmp_path):
    app_events = AppEvents()
    match_page, match_controller, weekly_service = make_match_controller(tmp_path, app_events)
    match_controller._settings_repository.save_last_result(_analysis_result())
    match_controller._roster_players = []

    calls = []
    app_events.weekly_plan_saved.connect(lambda: calls.append(True))

    match_controller._save_as_first_match()

    assert calls == [True]


def test_squad_controller_refreshes_weekly_planner_after_external_save(tmp_path):
    app_events = AppEvents()
    match_page, match_controller, weekly_service = make_match_controller(tmp_path, app_events)
    squad_page, squad_controller = make_squad_controller(tmp_path, app_events)

    refresh_calls = []
    original = squad_controller._show_weekly_training

    def tracked():
        refresh_calls.append(True)
        return original()

    squad_controller._show_weekly_training = tracked

    match_controller._settings_repository.save_last_result(_analysis_result())
    match_controller._roster_players = []
    match_controller._save_as_first_match()

    assert refresh_calls == [True]


def test_saved_first_match_is_planned_when_date_is_in_the_future(tmp_path):
    app_events = AppEvents()
    match_page, match_controller, weekly_service = make_match_controller(tmp_path, app_events)
    match_page.set_match_date("2026-08-02")
    match_controller._settings_repository.save_last_result(_analysis_result())
    match_controller._roster_players = []

    match_controller._save_as_first_match()

    record = weekly_service.first_match_record()
    assert record is not None
    assert record.opponent_name == "Rival FC"
    assert record.match_date.isoformat() == "2026-08-02"
    assert record.match_id == "2026-08-02:PLAYMAKING:first"
    assert record.planned_or_played.value == "PLANNED"


def test_saving_first_match_twice_does_not_duplicate(tmp_path):
    app_events = AppEvents()
    match_page, match_controller, weekly_service = make_match_controller(tmp_path, app_events)
    match_page.confirm_replace_first_match = lambda *args: True
    match_controller._settings_repository.save_last_result(_analysis_result())
    match_controller._roster_players = []

    match_controller._save_as_first_match()
    match_controller._save_as_first_match()

    state = weekly_service.load_state()
    first_match_records = [
        r for r in state.match_records if r.match_role.value == "FIRST_WEEKLY_MATCH"
    ]
    assert len(first_match_records) == 1


def test_training_priority_change_marks_open_match_analysis_stale(tmp_path):
    from dataclasses import replace

    app_events = AppEvents()
    match_page, match_controller, weekly_service = make_match_controller(tmp_path, app_events)
    cycle_id = weekly_service.active_cycle_id()
    result = match_controller._stamp_result_owner(replace(
        _analysis_result(match_type="CUP"),
        training_cycle_id=cycle_id,
        weekly_cycle_revision_used=weekly_service.weekly_cycle_revision(cycle_id),
        training_context_summary="context",
    ))
    match_controller._settings_repository.save_last_result(result)

    player = _player()
    weekly_service.save_priority(player, TrainingPriority.REQUIRED_50.value)
    app_events.weekly_plan_saved.emit()

    stale = match_controller._settings_repository.load_last_result()
    assert stale.training_context_stale is True
