import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from datetime import date

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
    page.set_match_type("LEAGUE")
    return page, controller, hist_repo


def test_date_field_defaults_to_today(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    assert page.match_date() == date.today().isoformat()


def test_set_match_date_updates_the_field(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.set_match_date("2026-09-15")
    assert page.match_date() == "2026-09-15"


def test_set_match_date_ignores_empty_input(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    original = page.match_date()
    page.set_match_date("")
    assert page.match_date() == original


def test_edit_record_restores_the_saved_date(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)
    assert page.match_date() == "2026-09-15"


def test_duplicate_detection_uses_the_selected_date_not_always_today(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )
    page.opponent_combo.setCurrentText("CA Chaco")
    page.set_match_date("2026-09-15")

    calls = []
    page.show_existing_match_dialog = lambda: calls.append(True) or True
    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is True
    assert calls == [True]


def test_different_date_for_same_opponent_is_not_flagged_as_existing(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )
    page.opponent_combo.setCurrentText("CA Chaco")
    page.set_match_date("2026-10-01")

    calls = []
    page.show_existing_match_dialog = lambda: calls.append(True) or True
    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is False
    assert calls == []


def test_editing_and_reanalyzing_with_restored_date_never_shows_dialog(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-09-15", competition_type="league"
    )
    controller.edit_record(record.snapshot_id)

    calls = []
    page.show_existing_match_dialog = lambda: calls.append(True) or True
    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is False
    assert calls == []
