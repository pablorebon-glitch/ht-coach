"""Alpha 0.6.7 HF-03, Parts 9-10: Official PRE is evidence, not an editor;
the tactic mismatch indicator.
"""
import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.official_ratings.models import OfficialRatingSnapshot, RatedAttribute
from engine.history.provisional_record import (
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
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
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.views.match_page import MatchPage
from models.opponent import Opponent
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


def _result(opponent="Rival", tactic="Attack in the Middle"):
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


def test_briefs_own_exact_scenario_aim_plan_aow_pre(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )
    pre = OfficialRatingSnapshot(
        tactic=RatedAttribute(label="Attack on Wings", level=10),
        canonical_tactic="Attack on Wings",
    )
    consolidate_with_official_pre(hist_repo, record, pre, "1")

    controller.edit_record(record.snapshot_id)
    page.show_results(_result(tactic="Attack in the Middle"))
    controller._update_pre_status_and_ratings_panel()

    text = page._tactic_mismatch_label.text()
    assert "no coincide" in text
    assert "Atacar por el centro" in text
    assert "Atacar por las bandas" in text


def test_matching_tactics_show_no_mismatch(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )
    pre = OfficialRatingSnapshot(
        tactic=RatedAttribute(label="Normal", level=5), canonical_tactic="Normal",
    )
    consolidate_with_official_pre(hist_repo, record, pre, "1")

    controller.edit_record(record.snapshot_id)
    page.show_results(_result(tactic="Normal"))
    controller._update_pre_status_and_ratings_panel()

    assert page._tactic_mismatch_label.text() == ""


def test_no_pre_shows_no_mismatch(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )

    page.opponent_combo.setCurrentText("Rival")
    page.set_match_date("2026-06-15")
    page.show_results(_result())
    controller._update_pre_status_and_ratings_panel()

    assert page._tactic_mismatch_label.text() == ""


def test_importing_pre_never_overwrites_the_current_plan_tactic(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )
    pre = OfficialRatingSnapshot(
        tactic=RatedAttribute(label="Attack on Wings", level=10),
        canonical_tactic="Attack on Wings",
    )
    consolidate_with_official_pre(hist_repo, record, pre, "1")

    controller.edit_record(record.snapshot_id)
    page.show_results(_result(tactic="Attack in the Middle"))
    controller._update_pre_status_and_ratings_panel()

    assert page.tactic() == "Attack in the Middle"


def test_importing_pre_never_overwrites_lineup_or_orders(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )
    consolidate_with_official_pre(hist_repo, record, OfficialRatingSnapshot(), "1")

    controller.edit_record(record.snapshot_id)
    result = _result()
    page.show_results(result)
    board_before = page._formation_board_widget.current_board()
    orders_before = {
        s.player.player_id: s.player.individual_order for s in board_before.slots if s.player
    }

    controller._update_pre_status_and_ratings_panel()

    board_after = page._formation_board_widget.current_board()
    orders_after = {
        s.player.player_id: s.player.individual_order for s in board_after.slots if s.player
    }
    assert orders_before == orders_after


def test_mismatch_indicator_compares_only_the_correctly_resolved_record(tmp_path):
    page, controller, hist_repo = make_controller(
        tmp_path, known_opponents=["Rival A", "Rival B"]
    )
    record_b = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival B", match_date="2026-08-16", competition_type="league"
    )
    pre_b = OfficialRatingSnapshot(
        tactic=RatedAttribute(label="Long Shots", level=10), canonical_tactic="Long Shots",
    )
    consolidate_with_official_pre(hist_repo, record_b, pre_b, "1")

    find_or_create_provisional_record(
        hist_repo, opponent_name="Rival A", match_date="2026-06-15", competition_type="league"
    )
    page.opponent_combo.setCurrentText("Rival A")
    page.set_match_date("2026-06-15")
    page.show_results(_result(opponent="Rival A", tactic="Normal"))

    controller._update_pre_status_and_ratings_panel()

    assert page._tactic_mismatch_label.text() == ""
