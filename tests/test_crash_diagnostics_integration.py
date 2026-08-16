"""Alpha 0.6.7 HF-03, Parts 13, 15, 16: diagnostics wiring into
MatchController.
"""
import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.diagnostics.app_context import current_context, reset_context
from ht_coach_app.diagnostics.event_buffer import recent_events, reset_event_buffer
from ht_coach_app.diagnostics.recovery_snapshot import RecoverySnapshotStore
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
    reset_context()
    reset_event_buffer()
    yield
    configure_localization("en")
    reset_context()
    reset_event_buffer()


def _lineup():
    return [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order="Normal", order_side="", player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]


def _result(opponent="Rival", match_type="LEAGUE"):
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Pressing", tactic_level=5,
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
    page.set_match_type("LEAGUE")
    return page, controller, hist_repo


def test_edit_record_updates_app_context(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )

    controller.edit_record(record.snapshot_id)

    context = current_context()
    assert context.active_page == "match"
    assert context.active_match_record_id == record.snapshot_id
    assert context.opponent_name == "Rival"


def test_edit_record_logs_switch_record_event(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )

    controller.edit_record(record.snapshot_id)

    events = recent_events()
    assert any(
        e.action == "switch_record" and e.match_record_id == record.snapshot_id
        for e in events
    )


def test_save_formation_logs_event(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    page.opponent_combo.setCurrentText("Rival")
    page.set_match_date("2026-06-15")
    controller._settings_repository.save_last_result(_result())

    controller._save_formation()

    events = recent_events()
    assert any(e.action == "save_formation" for e in events)


def test_switching_a_dirty_record_saves_a_recovery_snapshot(tmp_path):
    page, controller, hist_repo = make_controller(
        tmp_path, known_opponents=["Rival A", "Rival B"]
    )
    record_a = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival A", match_date="2026-06-15", competition_type="league"
    )
    record_b = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival B", match_date="2026-06-20", competition_type="league"
    )

    controller.edit_record(record_a.snapshot_id)
    page.show_results(_result(opponent="Rival A"))
    board = page._formation_board_widget
    index = board.tactic_combo.findData("Normal")
    board.tactic_combo.setCurrentIndex(index)

    page.confirm_unsaved_changes = lambda: "discard"
    controller.edit_record(record_b.snapshot_id)

    store = RecoverySnapshotStore()
    try:
        assert store.has_recovery_snapshot(record_a.snapshot_id)
    finally:
        store.discard(record_a.snapshot_id)


def test_saving_formation_discards_its_recovery_snapshot(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )
    store = RecoverySnapshotStore()
    store.save(record.snapshot_id, tactic="Normal")
    assert store.has_recovery_snapshot(record.snapshot_id)

    controller.edit_record(record.snapshot_id)
    page.show_results(_result())
    controller._settings_repository.save_last_result(_result())
    controller._save_formation()

    assert not store.has_recovery_snapshot(record.snapshot_id)


def test_deleting_a_record_logs_event(tmp_path):
    from ht_coach_app.controllers.saved_matches_controller import SavedMatchesController
    from ht_coach_app.views.saved_matches_page import SavedMatchesPage

    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival", match_date="2026-06-15", competition_type="league"
    )

    page = SavedMatchesPage()
    page.confirm_delete = lambda: True
    controller = SavedMatchesController(page, hist_repo)

    controller._delete_record(record.snapshot_id)

    events = recent_events()
    assert any(
        e.action == "delete_record" and e.match_record_id == record.snapshot_id
        for e in events
    )
