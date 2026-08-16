from pathlib import Path

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.calendar.season_calendar import SeasonCalendarConfig
from engine.calendar.season_calendar_repository import SeasonCalendarRepository
from engine.history.repository import HistoricalMatchRepository
from engine.weekly_training.models import MatchRole
from engine.weekly_training.persistence import WeeklyTrainingRepository
from ht_coach_app.controllers.match_controller import (
    MatchController,
    WORKSPACE_MODE_EDIT_SAVED_MATCH,
)
from ht_coach_app.controllers.saved_matches_controller import SavedMatchesController
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
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.state.app_events import AppEvents
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.views.saved_matches_page import SavedMatchesPage
from models.opponent import Opponent
from models.team_ratings import TeamRatings
from tests.test_official_rating_pre_post_formats import REAL_HF02_PRE


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _lineup():
    slots = [
        ("GOALKEEPER", "CENTER"),
        ("CENTRAL_DEFENDER", "LEFT"),
        ("CENTRAL_DEFENDER", "CENTER"),
        ("CENTRAL_DEFENDER", "RIGHT"),
        ("INNER_MIDFIELDER", "LEFT"),
        ("INNER_MIDFIELDER", "CENTER"),
        ("INNER_MIDFIELDER", "RIGHT"),
        ("WINGER", "LEFT"),
        ("WINGER", "RIGHT"),
        ("FORWARD", "LEFT"),
        ("FORWARD", "RIGHT"),
    ]
    return [
        LineupPlayerResult(
            number=index,
            position=position,
            side=side,
            order="Normal",
            order_side="",
            player_name=f"Jugador {index}",
        )
        for index, (position, side) in enumerate(slots, start=1)
    ]


def _analysis_result():
    formation = FormationAnalysisResult(
        formation_name="3-5-2",
        recommended_tactic="Pressing",
        tactic_level=8,
        win_probability=0.55,
        draw_probability=0.25,
        loss_probability=0.20,
        possession=52.0,
        expected_goals=1.7,
        opponent_expected_goals=1.1,
        is_recommended=True,
        team_ratings=TeamRatingsResult(),
        lineup=_lineup(),
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name="Santa Cruz Club",
        formations=[formation],
        players_csv_filename="players.csv",
        analyzed_formations=["3-5-2"],
        match_type="CUP",
    )


def _make_controller(tmp_path, settings_repo=None, app_events=None):
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_repo.save(Opponent(name="Santa Cruz Club", ratings=TeamRatings()))
    opponent_service = OpponentService(opponent_repo)
    weekly_repo = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_service = WeeklyTrainingAppService(repository=weekly_repo)
    settings_repo = settings_repo or MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json",
        result_storage_path=tmp_path / "result.json",
    )
    season_repo = SeasonCalendarRepository(tmp_path / "season.json")
    season_repo.save(
        SeasonCalendarConfig(
            season_number=95,
            season_start_date="2026-07-27",
        )
    )
    page = MatchPage()
    controller = MatchController(
        page,
        MatchWorkspaceService(opponent_service),
        settings_repo,
        app_events=app_events,
        weekly_training_service=weekly_service,
        official_rating_service=OfficialRatingImportService(repository=hist_repo),
        season_calendar_repository=season_repo,
    )
    return page, controller, hist_repo, weekly_repo, settings_repo


def _prepare_santa_cruz_workspace(page, controller):
    csv_path = str(Path("players.csv").resolve())
    page.set_players_csv_path(csv_path)
    controller._load_players()
    page.opponent_combo.setCurrentText("Santa Cruz Club")
    page.set_match_type("CUP")
    page.set_venue_role("home")
    page.set_match_date("2026-08-05")
    controller._analysis_finished(_analysis_result())


def _assert_round_trip(page, controller, record_id):
    assert controller._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH
    assert controller._active_match_record_id == record_id
    assert controller._editing_snapshot_id == record_id
    assert page.selected_opponent_name() == "Santa Cruz Club"
    assert page.match_type() == "CUP"
    assert page.venue_role() == "home"
    assert page.match_date() == "2026-08-05"
    assert len(controller._roster_players) == 18
    assert page.players_loaded_label.text() == "18 jugadores cargados"
    assert page._formation_board_widget is not None
    assert page._formation_board_widget.current_board().formation_name == "3-5-2"
    assert page.tactic() == "Pressing"


def test_santa_cruz_save_reads_the_persisted_json_record(tmp_path):
    page, controller, hist_repo, _weekly_repo, _settings = _make_controller(tmp_path)
    _prepare_santa_cruz_workspace(page, controller)

    controller._save_formation()

    payload = (tmp_path / "snapshots.json").read_text(encoding="utf-8")
    assert "Santa Cruz Club" in payload
    assert "Hit'em up - Santa Cruz Club" not in payload
    record = hist_repo.list_all()[0]
    assert record.match_context.opponent.opponent_name == "Santa Cruz Club"
    assert record.match_context.opponent.opponent_id == "Santa Cruz Club"
    assert record.match_context.competition_type.value == "cup"
    assert record.match_context.home_away.value == "home"
    assert record.match_context.match_date == "2026-08-05"
    assert record.ht_season_number == 95
    assert record.ht_season_week == 2
    assert record.training_cycle_id
    assert record.provenance.roster_source.endswith("players.csv")
    assert len(record.lineup) == 11
    assert record.tactical_setup.formation == "3-5-2"
    assert record.tactical_setup.selected_tactic == "Pressing"


def test_santa_cruz_saved_match_restores_and_saves_partido_2_without_new_match(tmp_path):
    app_events = AppEvents()
    page, controller, hist_repo, weekly_repo, settings_repo = _make_controller(
        tmp_path,
        app_events=app_events,
    )
    saved_page = SavedMatchesPage()
    saved_controller = SavedMatchesController(
        saved_page,
        hist_repo,
        weekly_repo,
        settings_repo,
        app_events,
    )
    saved_page.edit_requested.connect(controller.edit_record)

    _prepare_santa_cruz_workspace(page, controller)
    controller._save_formation()
    record = hist_repo.list_all()[0]
    saved_controller.refresh()
    saved_controller.open_record(record.snapshot_id)
    saved_page.edit_requested.emit(record.snapshot_id)

    _assert_round_trip(page, controller, record.snapshot_id)
    saved_controller.refresh()
    assert saved_page.table.item(0, 0).text() == "Hit'em up vs. Santa Cruz Club"
    assert saved_page.table.item(0, 1).text() == "Copa / Amistoso"
    assert saved_page.table.item(0, 2).text() == "05/08/2026"
    assert saved_page.table.item(0, 4).text() == "Local"

    controller._save_as_second_match()

    _assert_round_trip(page, controller, record.snapshot_id)
    assert page.status_label.text() == (
        "Guardado como Partido 2 en la semana del 02/08/2026 al 08/08/2026."
    )
    reloaded_weekly = WeeklyTrainingRepository(tmp_path / "planner.json").load()
    second = next(
        item
        for item in reloaded_weekly.match_records
        if item.match_role == MatchRole.SECOND_WEEKLY_MATCH
    )
    assert second.match_id == "2026-08-02:PLAYMAKING:second"
    assert second.linked_match_record_id == record.snapshot_id
    assert second.opponent_name == "Santa Cruz Club"
    assert second.competition_type.value == "CUP"
    assert second.match_date.isoformat() == "2026-08-05"
    assert len(hist_repo.list_all()) == 1


def test_saved_match_pre_import_and_save_changes_update_same_santa_cruz_record(tmp_path):
    app_events = AppEvents()
    page, controller, hist_repo, weekly_repo, settings_repo = _make_controller(
        tmp_path,
        app_events=app_events,
    )
    saved_page = SavedMatchesPage()
    saved_controller = SavedMatchesController(
        saved_page,
        hist_repo,
        weekly_repo,
        settings_repo,
        app_events,
    )
    saved_page.edit_requested.connect(controller.edit_record)

    _prepare_santa_cruz_workspace(page, controller)
    controller._save_as_second_match()
    original = hist_repo.list_all()[0]
    original_id = original.snapshot_id
    weekly_before = WeeklyTrainingRepository(tmp_path / "planner.json").load()
    second_before = next(
        item
        for item in weekly_before.match_records
        if item.match_role == MatchRole.SECOND_WEEKLY_MATCH
    )

    saved_controller.refresh()
    saved_controller.open_record(original_id)
    saved_page.edit_requested.emit(original_id)

    page.show_official_import_success = lambda: None
    page.show_official_import_error = lambda message: None
    page.confirm_official_import_replace = lambda slot: True
    controller._import_official_ratings(REAL_HF02_PRE, slot="pre")
    controller._save_formation()
    saved_controller.refresh()

    records = hist_repo.list_all()
    assert len(records) == 1
    record = records[0]
    assert record.snapshot_id == original_id
    assert controller._active_match_record_id == original_id
    assert controller._editing_snapshot_id == original_id
    assert record.official_pre is not None
    assert record.official_pre.hattrick_match_id == "770918226"
    assert record.match_context.official_match_id == "770918226"
    assert record.provenance.imported_match_id == "770918226"
    assert record.match_context.opponent.opponent_name == "Santa Cruz Club"
    assert record.match_context.opponent.opponent_name != "Hit'em up - Santa Cruz Club"
    assert record.match_context.competition_type.value == "cup"
    assert record.match_context.home_away.value == "home"
    assert record.match_context.match_date == "2026-08-05"
    assert saved_page.table.rowCount() == 1
    assert saved_page.table.item(0, 0).text() == "Hit'em up vs. Santa Cruz Club"
    assert saved_page.table.item(0, 1).text() == "Copa / Amistoso"
    assert saved_page.table.item(0, 2).text() == "05/08/2026"
    assert saved_page.table.item(0, 4).text() == "Local"

    weekly_after = WeeklyTrainingRepository(tmp_path / "planner.json").load()
    second_after = next(
        item
        for item in weekly_after.match_records
        if item.match_role == MatchRole.SECOND_WEEKLY_MATCH
    )
    assert second_after.match_id == second_before.match_id
    assert second_after.linked_match_record_id == original_id

    controller._import_official_ratings(REAL_HF02_PRE, slot="pre")
    controller._save_formation()
    reloaded = HistoricalMatchRepository(tmp_path / "snapshots.json").list_all()
    assert len(reloaded) == 1
    assert reloaded[0].snapshot_id == original_id


def test_saved_match_edit_blocks_import_when_active_record_id_is_missing(tmp_path):
    page, controller, hist_repo, _weekly_repo, _settings = _make_controller(tmp_path)
    _prepare_santa_cruz_workspace(page, controller)
    controller._save_formation()
    controller._active_match_record_id = ""
    page.show_official_import_error = lambda message: None

    controller._import_official_ratings(REAL_HF02_PRE, slot="pre")

    records = hist_repo.list_all()
    assert len(records) == 1
    assert records[0].official_pre is None


def test_saved_match_restores_from_snapshot_when_last_result_cache_is_missing(tmp_path):
    page, controller, hist_repo, _weekly_repo, settings_repo = _make_controller(tmp_path)
    _prepare_santa_cruz_workspace(page, controller)
    controller._save_formation()
    record_id = hist_repo.list_all()[0].snapshot_id
    settings_repo.clear_last_result()

    page2, controller2, _hist_repo2, _weekly_repo2, _settings2 = _make_controller(
        tmp_path,
        settings_repo=settings_repo,
    )
    controller2.edit_record(record_id)

    _assert_round_trip(page2, controller2, record_id)
    assert page2.status_label.text() == "Formación guardada restaurada"


def test_saved_match_restores_every_venue_role(tmp_path):
    for venue, expected in (
        ("home", "home"),
        ("away", "away"),
        ("neutral", "neutral"),
        ("unknown", "unknown"),
    ):
        page, controller, hist_repo, _weekly_repo, _settings = _make_controller(
            tmp_path / venue
        )
        _prepare_santa_cruz_workspace(page, controller)
        page.set_venue_role(venue)
        controller._save_formation()
        record_id = hist_repo.list_all()[0].snapshot_id

        page2, controller2, _hist_repo2, _weekly_repo2, _settings2 = _make_controller(
            tmp_path / venue
        )
        controller2.edit_record(record_id)
        assert page2.venue_role() == expected
