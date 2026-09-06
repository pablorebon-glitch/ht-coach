import os
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from engine.calendar import HTCalendarService
from engine.history.provisional_record import find_or_create_provisional_record
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services import ht_week_context_provider
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.ui.input_behavior import install_page_only_wheel_policy
from ht_coach_app.views.match_page import MatchPage
from models.opponent import Opponent
from models.team_ratings import TeamRatings
from tests.test_new_match_date_selector import make_controller


def _app():
    app = QApplication.instance() or QApplication([])
    install_page_only_wheel_policy(app)
    return app


def _show(widget):
    widget.resize(900, 700)
    widget.show()
    QApplication.processEvents()
    QTest.qWait(20)
    QApplication.processEvents()


def _calendar_page(page):
    calendar = page.match_date_edit.calendarWidget()
    return calendar.yearShown(), calendar.monthShown()


def _wheel(widget, delta=-120):
    center = widget.rect().center()
    event = QWheelEvent(
        QPointF(center),
        QPointF(widget.mapToGlobal(center)),
        QPoint(),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(widget, event)
    QApplication.processEvents()


def test_clicking_opponent_field_center_opens_popup_and_selection_works():
    _app()
    page = MatchPage()
    page.set_opponents(["Rival A", "Rival B"])
    _show(page)

    QTest.mouseClick(page.opponent_combo.lineEdit(), Qt.MouseButton.LeftButton)
    QApplication.processEvents()

    assert page.opponent_combo.view().isVisible()
    page.opponent_combo.setCurrentIndex(page.opponent_combo.findText("Rival B"))
    assert page.selected_opponent_name() == "Rival B"


def test_clicking_opponent_arrow_still_opens_popup():
    _app()
    page = MatchPage()
    page.set_opponents(["Rival A", "Rival B"])
    _show(page)

    QTest.mouseClick(
        page.opponent_combo,
        Qt.MouseButton.LeftButton,
        pos=page.opponent_combo.rect().center(),
    )
    QApplication.processEvents()

    assert page.opponent_combo.view().isVisible()


def test_opponent_combo_keyboard_navigation_still_selects_items():
    _app()
    page = MatchPage()
    page.set_opponents(["Rival A", "Rival B"])
    _show(page)

    page.opponent_combo.setFocus()
    page.opponent_combo.showPopup()
    QTest.keyClick(page.opponent_combo, Qt.Key_Down)
    QTest.keyClick(page.opponent_combo, Qt.Key_Down)
    QTest.keyClick(page.opponent_combo, Qt.Key_Return)

    assert page.selected_opponent_name() in {"Rival A", "Rival B"}


def test_opponent_combo_closed_wheel_does_not_change_selection():
    _app()
    page = MatchPage()
    page.set_opponents(["Rival A", "Rival B"])
    page.opponent_combo.setCurrentIndex(page.opponent_combo.findText("Rival A"))
    _show(page)

    before = page.selected_opponent_name()
    _wheel(page.opponent_combo, -120)

    assert page.selected_opponent_name() == before


def test_match_opponent_selector_uses_recently_created_order(tmp_path):
    _app()
    repository = OpponentRepository(storage_path=tmp_path / "opponents.json")
    repository.save(
        Opponent(
            name="Opponent A",
            ratings=TeamRatings(),
            created_at="2026-07-01T00:00:00",
        )
    )
    repository.save(
        Opponent(
            name="Opponent B",
            ratings=TeamRatings(),
            created_at="2026-08-20T00:00:00",
        )
    )
    repository.save(
        Opponent(
            name="Opponent C",
            ratings=TeamRatings(),
            created_at="2026-08-10T00:00:00",
        )
    )
    repository.save(Opponent(name="Legacy", ratings=TeamRatings()))
    service = OpponentService(repository)
    page = MatchPage()

    page.set_opponents([opponent.name for opponent in service.list_opponents_by_recency()])

    assert [page.opponent_combo.itemText(index) for index in range(1, 5)] == [
        "Opponent B",
        "Opponent C",
        "Opponent A",
        "Legacy",
    ]


def test_new_match_calendar_uses_current_month_from_injected_clock(tmp_path):
    _app()
    original_service = ht_week_context_provider.get_calendar_service()
    try:
        ht_week_context_provider.set_calendar_service(
            HTCalendarService(clock=lambda: datetime(2026, 8, 24, 12, 0, 0))
        )
        page, controller, _ = make_controller(tmp_path)
        page.match_date_edit.sync_calendar_page_to_selected_date()

        assert page.match_date() == "2026-08-24"
        assert _calendar_page(page) == (2026, 8)
    finally:
        ht_week_context_provider.set_calendar_service(original_service)


def test_new_match_resets_stale_calendar_page_from_previous_workspace(tmp_path):
    _app()
    original_service = ht_week_context_provider.get_calendar_service()
    try:
        ht_week_context_provider.set_calendar_service(
            HTCalendarService(clock=lambda: datetime(2026, 8, 24, 12, 0, 0))
        )
        page, controller, _ = make_controller(tmp_path)
        page.set_match_date("2027-07-15")
        assert _calendar_page(page) == (2027, 7)

        assert controller.start_new_match() is True

        assert page.match_date() == "2026-08-24"
        assert _calendar_page(page) == (2026, 8)
    finally:
        ht_week_context_provider.set_calendar_service(original_service)


def test_saved_match_calendar_opens_on_saved_date_month(tmp_path):
    _app()
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-07-26",
        competition_type="league",
    )

    controller.edit_record(record.snapshot_id)

    assert page.match_date() == "2026-07-26"
    assert _calendar_page(page) == (2026, 7)


def test_future_saved_match_calendar_opens_on_saved_date_month(tmp_path):
    _app()
    page, controller, hist_repo = make_controller(tmp_path, known_opponents=["CA Chaco"])
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2027-07-15",
        competition_type="league",
    )

    controller.edit_record(record.snapshot_id)

    assert page.match_date() == "2027-07-15"
    assert _calendar_page(page) == (2027, 7)


def test_clicking_match_date_field_center_opens_calendar_without_changing_date():
    _app()
    page = MatchPage()
    page.set_match_date("2026-08-05")
    _show(page)

    before = page.match_date()
    QTest.mouseClick(
        page.match_date_edit,
        Qt.MouseButton.LeftButton,
        pos=page.match_date_edit.rect().center(),
    )
    QApplication.processEvents()

    assert page.match_date_edit.calendarWidget().isVisible()
    assert page.match_date() == before
    assert _calendar_page(page) == (2026, 8)


def test_clicking_match_date_internal_text_editor_opens_calendar_without_caret_edit():
    _app()
    page = MatchPage()
    page.set_match_date("2026-08-05")
    _show(page)

    line_edit = page.match_date_edit.lineEdit()
    line_edit.setCursorPosition(0)
    before_date = page.match_date()
    before_cursor = line_edit.cursorPosition()

    QTest.mouseClick(
        line_edit,
        Qt.MouseButton.LeftButton,
        pos=line_edit.rect().center(),
    )
    QApplication.processEvents()

    assert page.match_date_edit.calendarWidget().isVisible()
    assert page.match_date() == before_date
    assert line_edit.cursorPosition() == before_cursor
    assert _calendar_page(page) == (2026, 8)


def test_clicking_match_date_arrow_still_opens_calendar_without_changing_date():
    _app()
    page = MatchPage()
    page.set_match_date("2026-08-05")
    _show(page)

    before = page.match_date()
    arrow_point = page.match_date_edit.rect().center()
    arrow_point.setX(page.match_date_edit.rect().right() - 4)
    QTest.mouseClick(
        page.match_date_edit,
        Qt.MouseButton.LeftButton,
        pos=arrow_point,
    )
    QApplication.processEvents()

    assert page.match_date_edit.calendarWidget().isVisible()
    assert page.match_date() == before
    assert _calendar_page(page) == (2026, 8)


def test_opening_match_date_calendar_preserves_saved_month():
    _app()
    page = MatchPage()
    page.set_match_date("2027-07-15")
    _show(page)

    page.match_date_edit.open_calendar_popup()
    QApplication.processEvents()

    assert page.match_date_edit.calendarWidget().isVisible()
    assert page.match_date() == "2027-07-15"
    assert _calendar_page(page) == (2027, 7)
