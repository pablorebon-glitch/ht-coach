"""Alpha 0.6.7 HF-03, Parts 5-6: "Guardar formación" -- the explicit save
action independent of Weekly Planner.
"""
from dataclasses import replace

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
QComboBox = pytest.importorskip("PySide6.QtWidgets").QComboBox

from engine.history.repository import HistoricalMatchRepository
from engine.weekly_training.persistence import WeeklyTrainingRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_workspace_service import (
    ANALYSIS_OWNER_SAVED_MATCH,
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    TeamRatingsResult,
)
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.views.match_page import MatchPage
from models.opponent import Opponent
from models.team_ratings import TeamRatings


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _lineup(orders=None):
    orders = orders or {}
    return [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order=orders.get(i, "Normal"), order_side="", player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]


def _result(opponent="Rival Histórico", tactic="Normal", tactic_level=5,
            formation_name="2-5-3", orders=None, match_type="LEAGUE"):
    formation = FormationAnalysisResult(
        formation_name=formation_name, recommended_tactic=tactic, tactic_level=tactic_level,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=_lineup(orders),
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name=opponent,
        formations=[formation],
        match_type=match_type,
    )


def make_controller(tmp_path, known_opponents=()):
    from engine.calendar.season_calendar import SeasonCalendarConfig
    from engine.calendar.season_calendar_repository import SeasonCalendarRepository

    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    for name in known_opponents:
        opponent_repo.save(Opponent(name=name, ratings=TeamRatings()))
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    official_service = OfficialRatingImportService(repository=hist_repo)
    weekly_service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    season_repo = SeasonCalendarRepository(tmp_path / "season_calendar.json")
    season_repo.save(
        SeasonCalendarConfig(
            season_number=95,
            season_start_date="2026-07-27",
        )
    )
    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo,
        weekly_training_service=weekly_service,
        official_rating_service=official_service,
        season_calendar_repository=season_repo,
    )
    page.set_match_type("LEAGUE")
    return page, controller, hist_repo, weekly_service


def test_save_formation_button_exists(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(tmp_path)
    page.show_results(_result())
    board = page._formation_board_widget
    assert board.save_formation_button is not None
    assert board.save_formation_button.text() == "Guardar formación"


def test_save_formation_persists_lineup_positions_and_orders(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path, known_opponents=["Rival Histórico"]
    )
    page.opponent_combo.setCurrentText("Rival Histórico")
    page.set_match_date("2026-06-15")

    controller._settings_repository.save_last_result(
        _result(orders={5: "Offensive"})
    )
    controller._save_formation()

    records = hist_repo.list_all()
    assert len(records) == 1
    record = records[0]
    assert len(record.lineup) == 11
    p5 = next(p for p in record.lineup if p.player_name == "P5")
    assert p5.individual_order == "Offensive"


def test_save_formation_persists_tactic_and_tactic_level(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path, known_opponents=["Rival Histórico"]
    )
    page.opponent_combo.setCurrentText("Rival Histórico")
    page.set_match_date("2026-06-15")

    controller._settings_repository.save_last_result(
        _result(tactic="Atacar por el centro", tactic_level=13)
    )
    controller._save_formation()

    record = hist_repo.list_all()[0]
    assert record.tactical_setup.selected_tactic == "Atacar por el centro"
    assert record.tactical_setup.tactic_level == 13


def test_save_formation_persists_formation_name(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path, known_opponents=["Rival Histórico"]
    )
    page.opponent_combo.setCurrentText("Rival Histórico")
    page.set_match_date("2026-06-15")

    controller._settings_repository.save_last_result(_result(formation_name="3-5-2"))
    controller._save_formation()

    record = hist_repo.list_all()[0]
    assert record.tactical_setup.formation == "3-5-2"


def test_save_formation_never_touches_weekly_planner(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path, known_opponents=["Rival Histórico"]
    )
    page.opponent_combo.setCurrentText("Rival Histórico")
    page.set_match_date("2026-06-15")

    controller._settings_repository.save_last_result(_result())
    controller._save_formation()

    state = weekly_service.load_state()
    assert state.match_records == ()


def test_save_formation_shows_confirmation(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path, known_opponents=["Rival Histórico"]
    )
    page.opponent_combo.setCurrentText("Rival Histórico")
    page.set_match_date("2026-06-15")

    controller._settings_repository.save_last_result(_result())
    controller._save_formation()

    assert page.status_label.text() == "Formación guardada"


def test_save_formation_works_for_a_historical_match_with_no_prior_record(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path, known_opponents=["Brand New Historical Rival"]
    )
    assert hist_repo.list_all() == ()

    page.opponent_combo.setCurrentText("Brand New Historical Rival")
    page.set_match_date("2026-03-01")
    controller._settings_repository.save_last_result(
        _result(opponent="Brand New Historical Rival")
    )
    controller._save_formation()

    records = hist_repo.list_all()
    assert len(records) == 1
    assert records[0].match_context.opponent.opponent_name == "Brand New Historical Rival"


def test_reopening_after_save_formation_restores_everything(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path, known_opponents=["Rival Histórico"]
    )
    page.opponent_combo.setCurrentText("Rival Histórico")
    page.set_match_date("2026-06-15")
    controller._settings_repository.save_last_result(
        _result(tactic="Presión", tactic_level=8, formation_name="3-5-2")
    )
    controller._save_formation()
    record = hist_repo.list_all()[0]

    match_service = MatchWorkspaceService(
        OpponentService(OpponentRepository(storage_path=tmp_path / "opponents.json"))
    )
    page2 = MatchPage()
    controller2 = MatchController(
        page2, match_service, controller._settings_repository,
        official_rating_service=controller._official_rating_service,
    )
    controller2.edit_record(record.snapshot_id)

    assert page2.selected_opponent_name() == "Rival Histórico"
    assert page2.match_date() == "2026-06-15"
    reloaded = hist_repo.get(record.snapshot_id)
    assert reloaded.tactical_setup.formation == "3-5-2"
    assert reloaded.tactical_setup.selected_tactic == "Presión"


def test_reopening_saved_match_prefers_persisted_lineup_over_cached_recommendation(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path, known_opponents=["Rival Histórico"]
    )
    page.opponent_combo.setCurrentText("Rival Histórico")
    page.set_match_date("2026-06-15")
    controller._settings_repository.save_last_result(
        _result(formation_name="2-5-3")
    )
    controller._save_formation()
    record = hist_repo.list_all()[0]

    controller._settings_repository.save_last_result(
        replace(
            _result(formation_name="3-5-2"),
            analysis_owner_type=ANALYSIS_OWNER_SAVED_MATCH,
            analysis_owner_id=record.snapshot_id,
        )
    )

    page2, controller2, _hist_repo2, _weekly_service2 = make_controller(
        tmp_path, known_opponents=["Rival Histórico"]
    )
    controller2.edit_record(record.snapshot_id)

    board = page2._formation_board_widget.current_board()
    assert board.formation_name == "2-5-3"
    assert hist_repo.get(record.snapshot_id).tactical_setup.formation == "2-5-3"


def test_new_match_save_persists_canonical_metadata_and_reopens_exactly(tmp_path):
    from ht_coach_app.controllers.saved_matches_controller import SavedMatchesController
    from ht_coach_app.views.saved_matches_page import SavedMatchesPage

    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path,
        known_opponents=["Santa Cruz Club"],
    )
    page.opponent_combo.setCurrentText("Santa Cruz Club")
    page.set_match_type("CUP")
    page.set_venue_role("home")
    page.set_match_date("2026-08-05")
    result = _result(opponent="Santa Cruz Club", match_type="CUP")
    controller._settings_repository.save_last_result(result)

    controller._save_formation()

    records = hist_repo.list_all()
    assert len(records) == 1
    record = records[0]
    assert record.match_context.opponent.opponent_name == "Santa Cruz Club"
    assert record.match_context.opponent.opponent_name != "Hit'em up - Santa Cruz Club"
    assert record.match_context.competition_type.value == "cup"
    assert record.match_context.home_away.value == "home"
    assert record.match_context.match_date == "2026-08-05"
    assert record.ht_season_number == 95
    assert record.ht_season_week == 2
    assert record.training_cycle_id

    saved_page = SavedMatchesPage()
    saved_controller = SavedMatchesController(saved_page, hist_repo)
    saved_controller.refresh()
    assert saved_page.table.item(0, 0).text() == "Hit'em up vs. Santa Cruz Club"
    assert saved_page.table.item(0, 1).text() == "Copa / Amistoso"
    assert saved_page.table.item(0, 2).text() == "05/08/2026"
    assert saved_page.table.item(0, 3).text() == "Temporada HT 95 · Semana competitiva 2"
    assert saved_page.table.item(0, 4).text() == "Local"

    page2, controller2, _hist_repo2, _weekly_service2 = make_controller(
        tmp_path,
        known_opponents=["Santa Cruz Club"],
    )
    controller2.edit_record(record.snapshot_id)
    assert page2.selected_opponent_name() == "Santa Cruz Club"
    assert page2.match_type() == "CUP"
    assert page2.venue_role() == "home"
    assert page2.match_date() == "2026-08-05"

    controller2._settings_repository.save_last_result(
        _result(opponent="Santa Cruz Club", match_type="CUP")
    )
    controller2._save_formation()
    assert len(hist_repo.list_all()) == 1


def test_save_formation_button_enabled_when_workspace_is_valid_after_analysis(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(
        tmp_path,
        known_opponents=["Rival Histórico"],
    )
    page.opponent_combo.setCurrentText("Rival Histórico")
    page.show_results(_result())
    board = page._formation_board_widget
    assert board.save_formation_button.isEnabled() is True


def test_save_formation_button_explains_missing_analysis(tmp_path):
    page, controller, hist_repo, weekly_service = make_controller(tmp_path)
    page.show_results(_result())
    page.clear_results()
    board = page._formation_board_widget
    page._update_save_action_labels()
    assert board.save_formation_button.isEnabled() is False
    assert board.save_formation_button.toolTip() == "Analizá un partido antes de guardar."


def test_save_formation_button_enabled_after_a_dirty_edit(tmp_path):
    import sys
    sys.path.insert(0, "tests")
    from test_interactive_workspace import (
        board_with_selected_forward,
        formation_result,
        roster_for_result,
    )

    from ht_coach_app.widgets.formation_board.formation_board import FormationBoard

    result = formation_result()
    widget = FormationBoard()
    widget.set_boards([board_with_selected_forward()], roster_players=roster_for_result(result))
    board = widget.current_board()
    slot = next(s for s in board.slots if s.player and s.player.position == "CENTRAL_DEFENDER")
    widget.select_player(slot.player.player_id)

    combo = widget.inspector.findChildren(QComboBox)[0]
    offensive_index = next(i for i in range(combo.count()) if combo.itemText(i) == "Offensive")
    combo.setCurrentIndex(offensive_index)

    assert widget.save_formation_button.isEnabled() is True
