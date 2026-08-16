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
from ht_coach_app.state.app_events import AppEvents
from ht_coach_app.views.match_page import MatchPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def make_controller(tmp_path, app_events=None):
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
        page, match_service, settings_repo, app_events=app_events,
        official_rating_service=official_service,
    )
    return page, controller, hist_repo


def test_no_existing_record_lets_analysis_proceed(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"

    assert controller._should_stop_for_existing_or_conflicting_match() is False


def test_exact_match_shows_dialog_and_stops_analysis(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    today = date.today().isoformat()
    find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="league"
    )
    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"
    page.show_existing_match_dialog = lambda: True

    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is True


def test_confirming_existing_match_dialog_emits_open_saved_match(tmp_path):
    app_events = AppEvents()
    page, controller, hist_repo = make_controller(tmp_path, app_events=app_events)
    today = date.today().isoformat()
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="league"
    )
    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"
    page.show_existing_match_dialog = lambda: True

    calls = []
    app_events.open_saved_match_requested.connect(calls.append)

    controller._should_stop_for_existing_or_conflicting_match()

    assert calls == [record.snapshot_id]


def test_declining_existing_match_dialog_resets_selectors_and_creates_nothing(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    today = date.today().isoformat()
    find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="league"
    )
    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"
    page.show_existing_match_dialog = lambda: False

    reset_calls = []
    page.reset_new_match_selectors = lambda: reset_calls.append(True)

    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is True
    assert reset_calls == [True]
    assert len(hist_repo.list_all()) == 1


def test_conflict_shows_dialog_with_both_competition_labels(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    today = date.today().isoformat()
    find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="cup"
    )
    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"

    calls = []
    page.show_match_conflict_dialog = lambda opp, existing, new: (
        calls.append((opp, existing, new)) or "cancel"
    )

    controller._should_stop_for_existing_or_conflicting_match()

    assert calls == [("CA Chaco", "Copa", "Liga")]


def test_conflict_create_new_lets_analysis_proceed(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    today = date.today().isoformat()
    find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="cup"
    )
    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"
    page.show_match_conflict_dialog = lambda *args: "create_new"

    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is False


def test_conflict_correct_updates_existing_record_competition_type(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    today = date.today().isoformat()
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="cup"
    )
    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"
    page.show_match_conflict_dialog = lambda *args: "correct"

    controller._should_stop_for_existing_or_conflicting_match()

    updated = hist_repo.get(record.snapshot_id)
    competition_value = getattr(
        updated.match_context.competition_type, "value", updated.match_context.competition_type
    )
    assert competition_value == "league"
    assert len(hist_repo.list_all()) == 1


def test_conflict_cancel_stops_without_changing_anything(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    today = date.today().isoformat()
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date=today, competition_type="cup"
    )
    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"
    page.show_match_conflict_dialog = lambda *args: "cancel"

    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is True
    unchanged = hist_repo.get(record.snapshot_id)
    competition_value = getattr(
        unchanged.match_context.competition_type, "value", unchanged.match_context.competition_type
    )
    assert competition_value == "cup"


def test_no_opponent_selected_never_triggers_a_dialog(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.selected_opponent_name = lambda: ""

    calls = []
    page.show_existing_match_dialog = lambda: calls.append(True) or True

    stopped = controller._should_stop_for_existing_or_conflicting_match()

    assert stopped is False
    assert calls == []


def test_view_without_dialog_support_never_blocks_analysis(tmp_path, monkeypatch):
    """The guard is `hasattr`-based -- if a view genuinely lacked both
    dialog methods, the check would short-circuit to False."""
    from ht_coach_app.views.match_page import MatchPage

    page, controller, hist_repo = make_controller(tmp_path)
    monkeypatch.delattr(MatchPage, "show_existing_match_dialog")
    monkeypatch.delattr(MatchPage, "show_match_conflict_dialog")

    page.selected_opponent_name = lambda: "CA Chaco"
    page.match_type = lambda: "LEAGUE"
    assert controller._should_stop_for_existing_or_conflicting_match() is False
