"""Alpha 0.6.7 HF-03, Parts 1-3, 11: Match workspace state isolation.
"""
import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.official_ratings.models import OfficialRatingSnapshot
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


def _result(opponent="CA Chaco", tactic="Normal"):
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


def test_part1_brand_new_match_never_inherits_another_records_pre(tmp_path):
    page, controller, hist_repo = make_controller(
        tmp_path, known_opponents=["pata2008", "Nuevo Rival"]
    )
    record_a = find_or_create_provisional_record(
        hist_repo, opponent_name="pata2008", match_date="2026-08-09", competition_type="league"
    )
    consolidate_with_official_pre(
        hist_repo, record_a, OfficialRatingSnapshot(team_name="Match A team"), "111222333"
    )

    page.opponent_combo.setCurrentText("Nuevo Rival")
    page.set_match_date("2026-08-16")
    page.show_results(_result(opponent="Nuevo Rival"))

    controller._update_pre_status_and_ratings_panel()

    assert page._pre_status_label.text() == "Falta importar el PRE oficial"
    assert controller._latest_official_pre_ratings() is None


def test_part11_switching_between_two_saved_matches_never_cross_contaminates(tmp_path):
    page, controller, hist_repo = make_controller(
        tmp_path, known_opponents=["Rival AIM", "Rival AOW"]
    )

    record_a = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival AIM", match_date="2026-08-09", competition_type="league"
    )

    record_b = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival AOW", match_date="2026-08-16", competition_type="league"
    )
    consolidate_with_official_pre(
        hist_repo, record_b, OfficialRatingSnapshot(team_name="B team"), "444555666"
    )

    controller.edit_record(record_a.snapshot_id)
    page.show_results(_result(opponent="Rival AIM"))
    controller._update_pre_status_and_ratings_panel()

    assert page.selected_opponent_name() == "Rival AIM"
    assert page._pre_status_label.text() == "Falta importar el PRE oficial"
    assert controller._latest_official_pre_ratings() is None


def test_reopening_a_record_with_its_own_pre_still_shows_it(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Rival Con PRE"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Rival Con PRE", match_date="2026-08-09", competition_type="league"
    )
    consolidate_with_official_pre(hist_repo, record, OfficialRatingSnapshot(), "999888777")

    controller.edit_record(record.snapshot_id)
    page.show_results(_result(opponent="Rival Con PRE"))
    controller._update_pre_status_and_ratings_panel()

    assert page._pre_status_label.text() == "PRE oficial cargado"


def test_editing_snapshot_id_takes_priority_over_opponent_lookup(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Editing Target"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Editing Target", match_date="2026-08-09", competition_type="league"
    )
    consolidate_with_official_pre(hist_repo, record, OfficialRatingSnapshot(), "1")

    controller._editing_snapshot_id = record.snapshot_id
    resolved = controller._current_workspace_record()

    assert resolved is not None
    assert resolved.snapshot_id == record.snapshot_id


def test_no_matching_record_returns_none_never_a_fallback_guess(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Solo Rival"])
    find_or_create_provisional_record(
        hist_repo, opponent_name="Different Rival Entirely", match_date="2026-08-09",
        competition_type="league",
    )

    page.opponent_combo.setCurrentText("Solo Rival")
    page.set_match_date("2026-08-09")

    assert controller._current_workspace_record() is None


def test_snapshot_id_override_bypasses_opponent_derivation_entirely(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["Irrelevant"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="Some Other Name", match_date="2026-08-09",
        competition_type="league",
    )
    consolidate_with_official_pre(hist_repo, record, OfficialRatingSnapshot(), "1")

    page.opponent_combo.setCurrentText("Irrelevant")
    resolved = controller._current_workspace_record(snapshot_id_override=record.snapshot_id)

    assert resolved is not None
    assert resolved.snapshot_id == record.snapshot_id
