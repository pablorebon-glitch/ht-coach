from datetime import datetime

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.calendar import HTCalendarService
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.ht_week_context_provider import (
    get_calendar_service,
    set_calendar_service,
)
from ht_coach_app.views.match_page import MatchPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    original = get_calendar_service()
    yield
    set_calendar_service(original)
    configure_localization("en")


def _row_for(page, widget):
    layout = page.analysis_inputs_panel.layout()
    index = layout.indexOf(widget)
    row, _column, _row_span, _column_span = layout.getItemPosition(index)
    return row


def test_match_preparation_fields_are_in_required_order():
    page = MatchPage()

    rows = [
        _row_for(page, page.opponent_label),
        _row_for(page, page.match_type_label),
        _row_for(page, page.venue_role_label),
        _row_for(page, page.match_date_label),
        _row_for(page, page.formation_label),
        _row_for(page, page.select_all_button.parentWidget()),
        _row_for(page, page.analyze_button),
    ]

    assert rows == sorted(rows)
    assert rows[-1] == _row_for(page, page.analyze_button)


def test_match_date_label_is_specific():
    page = MatchPage()
    assert page.match_date_label.text() == "Fecha del partido"


def test_new_match_date_uses_injected_clock_and_never_defaults_to_2027():
    set_calendar_service(
        HTCalendarService(clock=lambda: datetime(2026, 8, 2, 12, 0))
    )

    page = MatchPage()

    assert page.match_date() == "2026-08-02"
    assert not page.match_date().startswith("2027")


def test_analyze_button_is_last_and_waits_for_required_inputs():
    page = MatchPage()
    page.set_supported_formations(["3-5-2"], favorite_formations=["3-5-2"])

    assert page.analyze_button.isEnabled() is False

    page.players_path_edit.setText("players.csv")
    page.opponent_combo.addItem("Rival FC")
    page.opponent_combo.setCurrentText("Rival FC")
    page.set_match_type("LEAGUE")
    page.select_all_formations()

    assert page.analyze_button.isEnabled() is True
