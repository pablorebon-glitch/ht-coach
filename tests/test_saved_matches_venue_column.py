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


def make_controller(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    page = SavedMatchesPage()
    controller = SavedMatchesController(page, repository)
    return page, controller, repository


def test_table_has_six_columns_including_venue(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    assert page.table.columnCount() == 6


def test_venue_column_shows_home(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", home_away="home",
    )
    controller.refresh()
    assert page.table.item(0, 4).text() == "Local"


def test_venue_column_shows_away(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", home_away="away",
    )
    controller.refresh()
    assert page.table.item(0, 4).text() == "Visitante"


def test_venue_column_shows_neutral(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", home_away="neutral",
    )
    controller.refresh()
    assert page.table.item(0, 4).text() == "Cancha neutral"


def test_venue_column_shows_unknown_when_not_set(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.refresh()
    assert page.table.item(0, 4).text() == "Desconocido"


def test_status_column_is_still_after_venue(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller.refresh()
    assert page.table.item(0, 5).text()


def test_format_row_includes_venue_key(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", home_away="away",
    )
    row = SavedMatchesController._format_row(record)
    assert row["venue"] == "Visitante"
