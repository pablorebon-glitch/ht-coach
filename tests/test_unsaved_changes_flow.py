"""Alpha 0.6.7 HF-03, Part 12: unsaved changes flow when switching
records.
"""
import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.provisional_record import find_or_create_provisional_record
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


def _result(opponent="Rival A", tactic="Normal"):
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


def _make_dirty(page):
    board = page._formation_board_widget
    index = board.tactic_combo.findData("Pressing")
    board.tactic_combo.setCurrentIndex(index)


def _two_records(tmp_path):
    page, controller, hist_repo = make_controller(
        tmp_path, known_opponents=["Rival A", "Rival B"]
    )
    record_a = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival A", match_date="2026-06-15", competition_type="league"
    )
    record_b = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival B", match_date="2026-06-20", competition_type="league"
    )
    return page, controller, hist_repo, record_a, record_b


def test_no_prompt_when_workspace_is_clean(tmp_path):
    page, controller, hist_repo, record_a, record_b = _two_records(tmp_path)
    controller.edit_record(record_a.snapshot_id)
    page.show_results(_result())

    calls = []
    page.confirm_unsaved_changes = lambda: calls.append(True) or "cancel"
    controller.edit_record(record_b.snapshot_id)

    assert calls == []
    assert controller._editing_snapshot_id == record_b.snapshot_id


def test_cancel_stays_on_current_record(tmp_path):
    page, controller, hist_repo, record_a, record_b = _two_records(tmp_path)
    controller.edit_record(record_a.snapshot_id)
    page.show_results(_result())
    _make_dirty(page)

    page.confirm_unsaved_changes = lambda: "cancel"
    controller.edit_record(record_b.snapshot_id)

    assert controller._editing_snapshot_id == record_a.snapshot_id


def test_discard_switches_without_saving(tmp_path):
    page, controller, hist_repo, record_a, record_b = _two_records(tmp_path)
    controller.edit_record(record_a.snapshot_id)
    page.show_results(_result())
    _make_dirty(page)

    page.confirm_unsaved_changes = lambda: "discard"
    controller.edit_record(record_b.snapshot_id)

    assert controller._editing_snapshot_id == record_b.snapshot_id
    reloaded_a = hist_repo.get(record_a.snapshot_id)
    assert reloaded_a.lineup == ()


def test_save_persists_before_switching(tmp_path):
    page, controller, hist_repo, record_a, record_b = _two_records(tmp_path)
    controller.edit_record(record_a.snapshot_id)
    result = _result()
    page.show_results(result)
    controller._settings_repository.save_last_result(result)
    _make_dirty(page)

    page.confirm_unsaved_changes = lambda: "save"
    controller.edit_record(record_b.snapshot_id)

    assert controller._editing_snapshot_id == record_b.snapshot_id
    reloaded_a = hist_repo.get(record_a.snapshot_id)
    assert reloaded_a.tactical_setup.selected_tactic == "Pressing"


def test_changes_never_transfer_to_the_new_record(tmp_path):
    page, controller, hist_repo, record_a, record_b = _two_records(tmp_path)
    controller.edit_record(record_a.snapshot_id)
    page.show_results(_result())
    _make_dirty(page)

    page.confirm_unsaved_changes = lambda: "discard"
    controller.edit_record(record_b.snapshot_id)

    reloaded_b = hist_repo.get(record_b.snapshot_id)
    assert reloaded_b.tactical_setup.selected_tactic == ""


def test_reopening_the_same_record_never_prompts(tmp_path):
    page, controller, hist_repo, record_a, record_b = _two_records(tmp_path)
    controller.edit_record(record_a.snapshot_id)
    page.show_results(_result())
    _make_dirty(page)

    calls = []
    page.confirm_unsaved_changes = lambda: calls.append(True) or "cancel"
    controller.edit_record(record_a.snapshot_id)

    assert calls == []
