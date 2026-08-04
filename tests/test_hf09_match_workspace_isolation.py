from dataclasses import replace

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_controller import (
    ANALYSIS_OWNER_NEW_MATCH_DRAFT,
    ANALYSIS_OWNER_SAVED_MATCH,
    MatchController,
    WORKSPACE_MODE_EDIT_SAVED_MATCH,
    WORKSPACE_MODE_NEW_MATCH,
)
from ht_coach_app.core.localization import t
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


def make_controller(tmp_path, known_opponents=()):
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    for name in known_opponents:
        opponent_repo.save(Opponent(name=name, ratings=TeamRatings()))
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json",
        result_storage_path=tmp_path / "result.json",
    )
    official_service = OfficialRatingImportService(repository=hist_repo)
    page = MatchPage()
    controller = MatchController(
        page,
        match_service,
        settings_repo,
        official_rating_service=official_service,
    )
    return page, controller, hist_repo


def _result(opponent_name, owner_type="", owner_id=""):
    slots = [
        ("Goalkeeper (GK)", "Center"),
        ("Wing Back (WB)", "Left"),
        ("Central Defender (CD)", "Center"),
        ("Wing Back (WB)", "Right"),
        ("Winger (W)", "Left"),
        ("Inner Midfielder (IM)", "Left"),
        ("Inner Midfielder (IM)", "Center"),
        ("Inner Midfielder (IM)", "Right"),
        ("Winger (W)", "Right"),
        ("Forward (F)", "Left"),
        ("Forward (F)", "Right"),
    ]
    lineup = [
        LineupPlayerResult(
            number=index,
            position=position,
            side=side,
            order="Normal",
            order_side="",
            player_name=f"Player {index}",
        )
        for index, (position, side) in enumerate(slots, start=1)
    ]
    formation = FormationAnalysisResult(
        formation_name="3-5-2",
        recommended_tactic="Normal",
        tactic_level=5.0,
        win_probability=0.55,
        draw_probability=0.25,
        loss_probability=0.20,
        possession=52.0,
        expected_goals=1.8,
        opponent_expected_goals=1.1,
        is_recommended=True,
        team_ratings=TeamRatingsResult(),
        opponent_ratings=TeamRatingsResult(),
        lineup=lineup,
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name=opponent_name,
        formations=[formation],
        analysis_owner_type=owner_type,
        analysis_owner_id=owner_id,
    )


def test_new_match_start_clears_cached_results_from_other_workspace(tmp_path):
    page, controller, _hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    controller._settings_repository.save_last_result(
        _result("CA Chaco", ANALYSIS_OWNER_SAVED_MATCH, "saved-1")
    )

    assert controller.start_new_match() is True

    assert controller._workspace_mode == WORKSPACE_MODE_NEW_MATCH
    assert controller._editing_snapshot_id is None
    assert page.current_state() == "empty"
    assert page._formation_board_tab_container is None
    assert page.selected_opponent_name() == ""


def test_edit_saved_match_clears_stale_new_match_analysis(tmp_path):
    page, controller, hist_repo = make_controller(
        tmp_path,
        known_opponents=["CA Chaco", "Torres FC"],
    )
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-09-15",
        competition_type="league",
    )
    stale = _result(
        "Torres FC",
        ANALYSIS_OWNER_NEW_MATCH_DRAFT,
        "new-match:previous",
    )
    controller._settings_repository.save_last_result(stale)

    controller.edit_record(record.snapshot_id)

    assert controller._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH
    assert controller._active_match_record_id == record.snapshot_id
    assert page.selected_opponent_name() == "CA Chaco"
    assert page.current_state() == "empty"
    assert page._formation_board_tab_container is None
    assert page.status_label.text() == t("match.edit_requires_reanalysis")


def test_edit_saved_match_restores_only_analysis_owned_by_that_record(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-09-15",
        competition_type="league",
    )
    controller._settings_repository.save_last_result(
        _result("CA Chaco", ANALYSIS_OWNER_SAVED_MATCH, record.snapshot_id)
    )

    controller.edit_record(record.snapshot_id)

    assert page.current_state() == "success"
    assert page._formation_board_tab_container is not None


def test_same_opponent_result_for_different_saved_record_does_not_restore(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-09-15",
        competition_type="league",
    )
    controller._settings_repository.save_last_result(
        _result("CA Chaco", ANALYSIS_OWNER_SAVED_MATCH, "other-record")
    )

    controller.edit_record(record.snapshot_id)

    assert page.current_state() == "empty"
    assert page.status_label.text() == t("match.edit_requires_reanalysis")


def test_finished_analysis_is_stamped_with_current_workspace_owner(tmp_path):
    _page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-09-15",
        competition_type="league",
    )
    controller.edit_record(record.snapshot_id)

    stamped = controller._stamp_result_owner(_result("CA Chaco"))

    assert stamped.analysis_owner_type == ANALYSIS_OWNER_SAVED_MATCH
    assert stamped.analysis_owner_id == record.snapshot_id

    controller.start_new_match()
    stamped = controller._stamp_result_owner(replace(_result("CA Chaco"), formations=[]))

    assert stamped.analysis_owner_type == ANALYSIS_OWNER_NEW_MATCH_DRAFT
    assert stamped.analysis_owner_id.startswith("new-match:")


def test_analysis_owner_is_persisted_with_last_result_json(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-09-15",
        competition_type="league",
    )
    result = _result("CA Chaco", ANALYSIS_OWNER_SAVED_MATCH, record.snapshot_id)

    controller._settings_repository.save_last_result(result)
    restored = controller._settings_repository.load_last_result()

    assert restored.analysis_owner_type == ANALYSIS_OWNER_SAVED_MATCH
    assert restored.analysis_owner_id == record.snapshot_id
