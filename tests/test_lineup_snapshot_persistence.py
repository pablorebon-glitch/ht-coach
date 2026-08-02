import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.lineup_snapshot import build_historical_lineup, build_tactical_setup
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
            order="Normal", order_side="", player_name=f"Player {i}",
        )
        for i in range(1, 12)
    ]


def _formation():
    return FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Atacar por el centro", tactic_level=13,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=_lineup(),
    )


def _result(opponent="CA Chaco"):
    return MatchAnalysisResult(player_count=18, opponent_name=opponent, formations=[_formation()])


def make_controller(tmp_path):
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
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


def test_build_historical_lineup_converts_every_player():
    entries = build_historical_lineup(_formation())
    assert len(entries) == 11
    assert entries[0].player_name == "Player 1"
    assert entries[0].position == "INNER_MIDFIELDER"
    assert entries[0].individual_order == "Normal"


def test_build_tactical_setup_captures_formation_tactic_and_level():
    setup = build_tactical_setup(_formation())
    assert setup.formation == "2-5-3"
    assert setup.selected_tactic == "Atacar por el centro"
    assert setup.tactic_level == 13


def test_build_historical_lineup_handles_missing_lineup_gracefully():
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
    )
    assert build_historical_lineup(formation) == ()


def test_resolving_canonical_record_id_persists_the_lineup(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)

    snapshot_id = controller._linked_canonical_record_id(_result())

    record = hist_repo.get(snapshot_id)
    assert len(record.lineup) == 11
    assert record.tactical_setup.formation == "2-5-3"


def test_lineup_persistence_never_creates_a_duplicate_record(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)

    first_id = controller._linked_canonical_record_id(_result())
    second_id = controller._linked_canonical_record_id(_result())

    assert first_id == second_id
    assert len(hist_repo.list_all()) == 1


def test_editing_persists_lineup_to_the_record_being_edited(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    original_id = controller._linked_canonical_record_id(_result())
    controller._editing_snapshot_id = original_id

    updated_formation = FormationAnalysisResult(
        formation_name="4-4-2", recommended_tactic="Normal", tactic_level=7,
        win_probability=0.55, draw_probability=0.25, loss_probability=0.2,
        possession=52.0, expected_goals=1.6, opponent_expected_goals=1.1,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=_lineup(),
    )
    updated_result = MatchAnalysisResult(
        player_count=18, opponent_name="CA Chaco", formations=[updated_formation]
    )

    resolved_id = controller._linked_canonical_record_id(updated_result)

    assert resolved_id == original_id
    record = hist_repo.get(original_id)
    assert record.tactical_setup.formation == "4-4-2"


def test_lineup_persistence_failure_never_breaks_the_save_flow(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    controller._persist_lineup_to_canonical_record("does-not-exist", _result())


def test_no_history_repository_never_breaks_id_resolution(tmp_path):
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    page = MatchPage()
    controller = MatchController(page, match_service, settings_repo)
    assert controller._linked_canonical_record_id(_result()) == ""
