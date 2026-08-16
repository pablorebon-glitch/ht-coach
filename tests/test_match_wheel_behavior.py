import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QScrollArea,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.ui.input_behavior import install_page_only_wheel_policy
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.widgets.formation_board.formation_board import FormationBoard
from tests.test_interactive_workspace import (
    board_with_selected_forward,
    formation_result,
    roster_for_result,
)
from tests.test_match_collapsible_sections import rich_match_result


def _app():
    app = QApplication.instance() or QApplication([])
    install_page_only_wheel_policy(app)
    return app


def _show_page(page, width=1366, height=620):
    page.resize(width, height)
    page.show()
    QApplication.processEvents()
    QTest.qWait(20)
    QApplication.processEvents()


def _wheel(widget, delta=-120):
    center = widget.rect().center()
    global_pos = widget.mapToGlobal(center)
    event = QWheelEvent(
        QPointF(center),
        QPointF(global_pos),
        QPoint(),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(widget, event)
    QApplication.processEvents()
    return event


def _assert_wheel_scrolls_page_without_changing(page, widget, value_getter):
    scroll = page.scroll_area.verticalScrollBar()
    scroll.setValue(0)
    before_value = value_getter()
    before_scroll = scroll.value()

    _wheel(widget, -120)

    assert value_getter() == before_value
    if scroll.maximum() > 0:
        assert scroll.value() > before_scroll


def test_match_input_combos_ignore_closed_wheel_and_scroll_page():
    _app()
    page = MatchPage()
    page.show_results(rich_match_result())
    _show_page(page)

    controls = [
        page.recent_csv_combo,
        page.availability_combo,
        page.opponent_combo,
        page.match_type_combo,
        page.venue_role_combo,
    ]
    for combo in controls:
        combo.setFocus()
        changed = []
        combo.currentIndexChanged.connect(changed.append)
        _assert_wheel_scrolls_page_without_changing(
            page,
            combo,
            combo.currentIndex,
        )
        assert changed == []


def test_match_date_edit_ignores_wheel_and_scrolls_page():
    _app()
    page = MatchPage()
    page.show_results(rich_match_result())
    _show_page(page)

    changed = []
    page.match_date_edit.dateChanged.connect(changed.append)
    _assert_wheel_scrolls_page_without_changing(
        page,
        page.match_date_edit,
        page.match_date_edit.date,
    )
    assert changed == []


def test_formation_tactic_and_attitude_ignore_wheel_without_emitting():
    _app()
    page = MatchPage()
    page.show_results(rich_match_result())
    _show_page(page)
    board = page.findChild(FormationBoard)
    assert board is not None

    signal_counts = {
        "formation": 0,
        "tactic": 0,
        "attitude": 0,
    }
    board.formation_changed.connect(
        lambda *_: signal_counts.__setitem__(
            "formation", signal_counts["formation"] + 1
        )
    )
    board.tactic_changed.connect(
        lambda *_: signal_counts.__setitem__(
            "tactic", signal_counts["tactic"] + 1
        )
    )
    board.team_attitude_changed.connect(
        lambda *_: signal_counts.__setitem__(
            "attitude", signal_counts["attitude"] + 1
        )
    )

    for combo in (
        board.formation_combo,
        board.tactic_combo,
        board.team_attitude_combo,
    ):
        _assert_wheel_scrolls_page_without_changing(
            page,
            combo,
            combo.currentIndex,
        )

    assert signal_counts == {
        "formation": 0,
        "tactic": 0,
        "attitude": 0,
    }
    assert board.is_dirty() is False


def test_player_order_combo_ignores_wheel_without_dirtying_workspace():
    _app()
    scroll_area = QScrollArea()
    scroll_area.setObjectName("matchPageScroll")
    scroll_area.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.addWidget(QLabel("Top spacer"))
    board = FormationBoard()
    result = formation_result()
    board.set_boards(
        [board_with_selected_forward()],
        roster_players=roster_for_result(result),
    )
    editable_slot = next(
        slot
        for slot in board.current_board().slots
        if slot.player is not None and slot.player.position == "CENTRAL_DEFENDER"
    )
    board.select_player(editable_slot.player.player_id)
    layout.addWidget(board)
    for index in range(12):
        layout.addWidget(QLabel(f"Bottom spacer {index}"))
    scroll_area.setWidget(content)
    scroll_area.resize(1366, 620)
    scroll_area.show()
    QApplication.processEvents()
    QTest.qWait(20)
    QApplication.processEvents()

    order_combo = board.inspector.findChild(QComboBox, "playerOrderCombo")
    assert order_combo is not None
    modified = []
    board.workspace_modified.connect(modified.append)

    scroll = scroll_area.verticalScrollBar()
    scroll.setValue(0)
    before_index = order_combo.currentIndex()
    before_scroll = scroll.value()
    _wheel(order_combo, -120)

    assert order_combo.currentIndex() == before_index
    if scroll.maximum() > 0:
        assert scroll.value() > before_scroll
    assert modified == []
    assert board.is_dirty() is False


def test_match_result_tabs_ignore_wheel_and_scroll_page():
    _app()
    page = MatchPage()
    page.show_results(rich_match_result())
    _show_page(page)
    tabs = page.findChild(QTabBar)
    assert tabs is not None
    changed = []
    page._result_tabs.currentChanged.connect(changed.append)

    _assert_wheel_scrolls_page_without_changing(
        page,
        tabs,
        page._result_tabs.currentIndex,
    )
    assert changed == []


def test_bottom_scroll_limit_does_not_change_tabs_or_selectors():
    _app()
    page = MatchPage()
    page.show_results(rich_match_result())
    _show_page(page)
    scroll = page.scroll_area.verticalScrollBar()
    scroll.setValue(scroll.maximum())
    tab_index = page._result_tabs.currentIndex()
    tactic_index = page._formation_board_widget.tactic_combo.currentIndex()

    _wheel(page._formation_board_widget.tactic_combo, -120)
    _wheel(page._result_tabs.tabBar(), -120)

    assert page._result_tabs.currentIndex() == tab_index
    assert page._formation_board_widget.tactic_combo.currentIndex() == tactic_index
    assert scroll.value() == scroll.maximum()


def test_open_combo_popup_is_not_protected_by_closed_combo_policy():
    app = _app()
    combo = QComboBox()
    for index in range(30):
        combo.addItem(f"Option {index}")
    combo.show()
    QApplication.processEvents()

    event_filter = install_page_only_wheel_policy(app)
    combo.showPopup()
    QApplication.processEvents()

    try:
        assert event_filter._protected_value_widget(combo) is None
    finally:
        combo.hidePopup()
        combo.close()
