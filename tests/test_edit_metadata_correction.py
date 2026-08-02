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


def _result(opponent="CA Chaco"):
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=_lineup(),
    )
    return MatchAnalysisResult(player_count=18, opponent_name=opponent, formations=[formation])


def make_controller(tmp_path, known_opponents=()):
    from engine.weekly_training.persistence import WeeklyTrainingRepository
    from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService

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
    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo, weekly_training_service=weekly_service,
        official_rating_service=official_service,
    )
    return page, controller, hist_repo


def test_edit_restores_venue_role_to_the_view(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", home_away="away",
    )
    controller.edit_record(record.snapshot_id)
    assert page.venue_role() == "away"


def test_correcting_competition_type_persists_to_canonical_record(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)
    controller._settings_repository.save_last_result(_result())

    page.set_match_type("CUP")
    controller._save_as_first_match()

    updated = hist_repo.get(record.snapshot_id)
    assert updated.match_context.competition_type.value == "cup"


def test_correcting_venue_role_persists_to_canonical_record(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)
    controller._settings_repository.save_last_result(_result())

    page.set_venue_role("neutral")
    controller._save_as_first_match()

    updated = hist_repo.get(record.snapshot_id)
    assert updated.match_context.home_away.value == "neutral"


def test_correcting_metadata_never_creates_a_duplicate_record(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)
    controller._settings_repository.save_last_result(_result())

    page.set_match_type("CUP")
    page.set_venue_role("home")
    controller._save_as_first_match()

    assert len(hist_repo.list_all()) == 1


def test_correcting_metadata_preserves_the_official_match_id(tmp_path):
    from engine.history.official_ratings.models import OfficialRatingSnapshot
    from engine.history.provisional_record import consolidate_with_official_pre

    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    record = consolidate_with_official_pre(hist_repo, record, OfficialRatingSnapshot(), "770918226")

    controller.edit_record(record.snapshot_id)
    controller._settings_repository.save_last_result(_result())

    page.set_match_type("CUP")
    controller._save_as_first_match()

    updated = hist_repo.get(record.snapshot_id)
    assert updated.match_context.official_match_id == "770918226"


def test_correcting_metadata_never_touches_the_opponent_identity(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)
    controller._settings_repository.save_last_result(_result())

    page.set_venue_role("away")
    controller._save_as_first_match()

    updated = hist_repo.get(record.snapshot_id)
    assert updated.match_context.opponent.opponent_name == "CA Chaco"


def test_not_editing_any_record_never_triggers_metadata_correction(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    controller._settings_repository.save_last_result(_result())

    controller._save_as_first_match()

    assert controller._editing_snapshot_id is None
