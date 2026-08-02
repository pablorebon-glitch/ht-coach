import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_workspace_service import MatchWorkspaceService
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


def test_edit_record_restores_opponent(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)
    assert page.selected_opponent_name() == "CA Chaco"


def test_edit_record_restores_opponent_even_if_not_in_opponent_manager(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=[])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)
    assert page.selected_opponent_name() == "CA Chaco"


def test_edit_record_opens_preparation_section_and_marks_edit_mode(tmp_path):
    from ht_coach_app.core.localization import t

    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    page.collapse_analysis_inputs()

    controller.edit_record(record.snapshot_id)

    assert page.analysis_inputs_expanded()
    assert page.analysis_setup_title.text() == t("match.editing_saved_match")


def test_edit_record_restores_competition_type(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="cup"
    )
    controller.edit_record(record.snapshot_id)
    assert page.match_type() == "CUP"


def test_edit_record_tracks_which_record_is_being_edited(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)
    assert controller._editing_snapshot_id == record.snapshot_id


def test_reanalyzing_the_record_being_edited_never_shows_duplicate_dialog(tmp_path):
    from datetime import date

    today = date.today().isoformat()
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="league"
    )
    controller.edit_record(record.snapshot_id)

    calls = []
    page.show_existing_match_dialog = lambda: calls.append(True) or True

    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is False
    assert calls == []


def test_editing_a_different_match_after_still_triggers_normal_detection(tmp_path):
    from datetime import date

    today = date.today().isoformat()
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco", "Torres FC"])
    record_a = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="league"
    )
    record_b = find_or_create_provisional_record(
        hist_repo, opponent_name="Torres FC", match_date=today, competition_type="league"
    )
    controller.edit_record(record_a.snapshot_id)

    page.opponent_combo.setCurrentText("Torres FC")
    calls = []
    page.show_existing_match_dialog = lambda: calls.append(True) or True

    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is True
    assert calls == [True]


def test_edit_nonexistent_record_does_not_crash(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    controller.edit_record("does-not-exist")
    assert controller._editing_snapshot_id is None


def test_edit_without_history_repository_does_not_crash(tmp_path):
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    page = MatchPage()
    controller = MatchController(page, match_service, settings_repo)
    controller.edit_record("anything")


def test_edit_without_matching_cached_result_shows_reanalysis_message(tmp_path):
    from ht_coach_app.core.localization import t

    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )

    controller.edit_record(record.snapshot_id)

    assert page.status_label.text() == t("match.edit_requires_reanalysis")


def test_edit_with_matching_cached_result_restores_full_workspace(tmp_path):
    from ht_coach_app.services.match_workspace_service import (
        FormationAnalysisResult,
        LineupPlayerResult,
        MatchAnalysisResult,
        TeamRatingsResult,
    )

    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )

    lineup = [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order="Normal", order_side="", player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=lineup,
    )
    cached_result = MatchAnalysisResult(player_count=18, opponent_name="CA Chaco", formations=[formation])

    controller._settings_repository.save_last_result(cached_result)

    controller.edit_record(record.snapshot_id)

    assert page._formation_board_tab_container is not None
    assert page._state == "success"


def test_edit_with_cached_result_for_a_different_opponent_does_not_restore(tmp_path):
    from ht_coach_app.services.match_workspace_service import (
        FormationAnalysisResult,
        LineupPlayerResult,
        MatchAnalysisResult,
        TeamRatingsResult,
    )
    from ht_coach_app.core.localization import t

    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco", "Torres FC"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )

    lineup = [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order="Normal", order_side="", player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=lineup,
    )
    cached_result = MatchAnalysisResult(player_count=18, opponent_name="Torres FC", formations=[formation])
    controller._settings_repository.save_last_result(cached_result)

    controller.edit_record(record.snapshot_id)

    assert page.status_label.text() == t("match.edit_requires_reanalysis")


def test_editing_metadata_marks_workspace_dirty_and_saves_without_reanalysis(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco", "Torres FC"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )

    controller.edit_record(record.snapshot_id)
    page.opponent_combo.setCurrentText("Torres FC")
    page.set_match_type("CUP")
    page.set_venue_role("away")
    controller._save_formation()

    updated = hist_repo.get(record.snapshot_id)
    assert updated.match_context.opponent.opponent_name == "Torres FC"
    assert updated.match_context.competition_type.value == "cup"
    assert updated.match_context.home_away.value == "away"
    assert page.is_workspace_dirty() is False


def test_editing_metadata_with_official_evidence_shows_warning_and_preserves_match_id(tmp_path):
    from engine.history.official_ratings.models import OfficialRatingSnapshot
    from engine.history.provisional_record import consolidate_with_official_pre
    from ht_coach_app.core.localization import t

    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco", "Torres FC"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )
    record = consolidate_with_official_pre(
        hist_repo, record, OfficialRatingSnapshot(), "770918226"
    )

    controller.edit_record(record.snapshot_id)
    page.opponent_combo.setCurrentText("Torres FC")

    assert page.metadata_evidence_warning_label.text() == t(
        "match.metadata_official_evidence_warning"
    )

    controller._save_formation()
    updated = hist_repo.get(record.snapshot_id)
    assert updated.match_context.official_match_id == "770918226"
    assert updated.official_pre is not None


def test_weekly_save_button_labels_are_compact(tmp_path):
    from ht_coach_app.core.localization import t
    from ht_coach_app.services.match_workspace_service import (
        FormationAnalysisResult,
        LineupPlayerResult,
        MatchAnalysisResult,
        TeamRatingsResult,
    )

    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    lineup = [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order="Normal", order_side="", player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]
    formation = FormationAnalysisResult(
        formation_name="3-5-2", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=lineup,
    )
    page.show_results(
        MatchAnalysisResult(player_count=18, opponent_name="CA Chaco", formations=[formation])
    )

    board = page._formation_board_widget
    assert board.save_as_first_match_button.text() == t("match.save_as_first_match")
    assert board.save_as_second_match_button.text() == t("match.save_as_second_match")
