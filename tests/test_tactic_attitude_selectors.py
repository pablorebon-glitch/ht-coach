"""Alpha 0.6.7 HF-03, Parts 7-8: canonical tactic and team attitude
selectors.
"""
import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.core.tactic_formatting import canonical_tactic_choices, format_tactic
from ht_coach_app.core.team_attitude_formatting import (
    canonical_team_attitude_choices,
    format_team_attitude,
)
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
from ht_coach_app.views.match_page import MatchPage
from models.opponent import Opponent
from models.tactic import Tactic
from models.team_ratings import TeamRatings


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


def _result(opponent="Rival", tactic="Normal"):
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic=tactic, tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=_lineup(),
    )
    return MatchAnalysisResult(player_count=18, opponent_name=opponent, formations=[formation])


def make_controller(tmp_path, known_opponents=()):
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
    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo, official_rating_service=official_service,
    )
    return page, controller, hist_repo


def test_tactic_catalog_matches_the_briefs_exact_list():
    labels = [label for _, label in canonical_tactic_choices()]
    assert labels == [
        "Normal", "Atacar por el centro", "Atacar por las bandas",
        "Presión", "Contraataques", "Jugar creativamente", "Tiros lejanos",
    ]


def test_tactic_catalog_never_invents_unsupported_tactics():
    tactics = [tactic for tactic, _ in canonical_tactic_choices()]
    assert set(tactics) == set(Tactic)


def test_team_attitude_catalog_matches_the_brief():
    labels = [label for _, label in canonical_team_attitude_choices()]
    assert labels == ["Normal", "PIC / Jugar relajados", "MOTS / Partido de la temporada"]


def test_format_tactic_accepts_raw_string_values():
    assert format_tactic("Pressing") == "Presión"


def test_format_team_attitude_accepts_raw_string_values():
    assert format_team_attitude("Match of the Season") == "MOTS / Partido de la temporada"


def test_tactic_selector_defaults_to_the_recommended_tactic(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result(tactic="Counter-Attacks"))
    board = page._formation_board_widget
    assert board.tactic_combo.currentData() == "Counter-Attacks"
    assert board.tactic_combo.currentText() == "Contraataques"


def test_changing_tactic_marks_workspace_dirty(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    board = page._formation_board_widget
    assert board.save_formation_button.isEnabled() is False

    index = board.tactic_combo.findData("Pressing")
    board.tactic_combo.setCurrentIndex(index)

    assert board.save_formation_button.isEnabled() is True


def test_changing_team_attitude_marks_workspace_dirty(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    board = page._formation_board_widget
    assert board.save_formation_button.isEnabled() is False

    index = board.team_attitude_combo.findData("Play it Cool")
    board.team_attitude_combo.setCurrentIndex(index)

    assert board.save_formation_button.isEnabled() is True


def test_changing_tactic_emits_signal(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())

    calls = []
    page.tactic_changed.connect(calls.append)

    board = page._formation_board_widget
    index = board.tactic_combo.findData("Long Shots")
    board.tactic_combo.setCurrentIndex(index)

    assert calls == ["Long Shots"]


def test_saving_persists_the_user_selected_tactic_not_the_recommendation(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    page.opponent_combo.setCurrentText("Rival")
    page.set_match_date("2026-06-15")
    result = _result(tactic="Normal")
    page.show_results(result)
    controller._settings_repository.save_last_result(result)

    board = page._formation_board_widget
    index = board.tactic_combo.findData("Pressing")
    board.tactic_combo.setCurrentIndex(index)

    controller._save_formation()

    record = hist_repo.list_all()[0]
    assert record.tactical_setup.selected_tactic == "Pressing"


def test_saving_persists_the_user_selected_team_attitude(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    page.opponent_combo.setCurrentText("Rival")
    page.set_match_date("2026-06-15")
    result = _result()
    page.show_results(result)
    controller._settings_repository.save_last_result(result)

    board = page._formation_board_widget
    index = board.team_attitude_combo.findData("Match of the Season")
    board.team_attitude_combo.setCurrentIndex(index)

    controller._save_formation()

    record = hist_repo.list_all()[0]
    assert record.tactical_setup.team_attitude == "Match of the Season"


def test_changing_tactic_never_alters_player_selection(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    board = page._formation_board_widget
    board_state_before = board.current_board()
    orders_before = {
        s.player.player_id: s.player.individual_order
        for s in board_state_before.slots if s.player
    }

    index = board.tactic_combo.findData("Pressing")
    board.tactic_combo.setCurrentIndex(index)

    board_state_after = board.current_board()
    orders_after = {
        s.player.player_id: s.player.individual_order
        for s in board_state_after.slots if s.player
    }
    assert orders_before == orders_after


def test_changing_team_attitude_never_touches_official_pre(tmp_path):
    from engine.history.official_ratings.models import OfficialRatingSnapshot
    from engine.history.provisional_record import (
        consolidate_with_official_pre,
        find_or_create_provisional_record,
    )

    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )
    consolidate_with_official_pre(
        hist_repo, record, OfficialRatingSnapshot(team_name="Original PRE"), "1"
    )

    controller.edit_record(record.snapshot_id)
    page.show_results(_result())
    board = page._formation_board_widget
    index = board.team_attitude_combo.findData("Play it Cool")
    board.team_attitude_combo.setCurrentIndex(index)

    reloaded = hist_repo.get(record.snapshot_id)
    assert reloaded.official_pre is not None
    assert reloaded.official_pre.team_name == "Original PRE"
