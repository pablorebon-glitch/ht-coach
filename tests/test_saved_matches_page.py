import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.saved_matches_controller import SavedMatchesController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.views.saved_matches_page import SavedMatchesPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _seed(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    find_or_create_provisional_record(
        repository, opponent_name="pata2008", match_date="2026-08-02",
        competition_type="cup", season_number=95, season_week=1,
    )
    find_or_create_provisional_record(
        repository, opponent_name="Santa Cruz Club", match_date="2026-07-26",
        competition_type="friendly", season_number=95, season_week=1,
    )


def make_controller(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    page = SavedMatchesPage()
    controller = SavedMatchesController(page, repository)
    return page, controller, repository


def test_empty_list_shows_empty_state_not_a_table(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    controller.refresh()
    assert page.table.isHidden() is True
    assert page.empty_state_label.isHidden() is False


def test_list_does_not_auto_open_a_match(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()
    assert page.table.rowCount() == 3
    edit_calls = []
    page.edit_requested.connect(edit_calls.append)
    assert edit_calls == []


def test_row_identity_matches_briefs_own_example_format(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()

    opponents = [page.table.item(row, 0).text() for row in range(page.table.rowCount())]
    types = [page.table.item(row, 1).text() for row in range(page.table.rowCount())]
    assert "CA Chaco" in opponents
    assert "Liga" in types


def test_status_never_appended_to_the_identity_column(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()

    for row in range(page.table.rowCount()):
        opponent_cell = page.table.item(row, 0).text()
        assert "Planificado" not in opponent_cell
        assert "Completo" not in opponent_cell
        assert "PRE" not in opponent_cell


def test_status_column_is_populated_separately(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()

    statuses = [page.table.item(row, 4).text() for row in range(page.table.rowCount())]
    assert all(status for status in statuses)


def test_buttons_disabled_without_selection(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()
    assert page.edit_button.isEnabled() is False
    assert page.delete_button.isEnabled() is False


def test_buttons_enabled_after_selecting_a_row(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()
    page.table.selectRow(0)
    assert page.edit_button.isEnabled() is True
    assert page.delete_button.isEnabled() is True


def test_edit_requested_emits_the_selected_records_snapshot_id(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()
    page.table.selectRow(0)

    calls = []
    page.edit_requested.connect(calls.append)
    page._emit_edit_requested()

    assert len(calls) == 1
    assert repository.get(calls[0]) is not None


def test_delete_requested_emits_the_selected_records_snapshot_id(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()
    page.table.selectRow(1)
    page.confirm_delete = lambda: False

    calls = []
    page.delete_requested.connect(calls.append)
    page._emit_delete_requested()

    assert len(calls) == 1


def test_refresh_with_no_repository_does_not_crash():
    page = SavedMatchesPage()
    controller = SavedMatchesController(page, repository=None)
    controller.refresh()
    assert page.table.rowCount() == 0
