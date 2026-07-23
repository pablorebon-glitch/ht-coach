import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget
from PySide6.QtTest import QTest

from ht_coach_app.ui.design_system.collapsible_section import CollapsibleSection
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceSettings,
)
from ht_coach_app.ui.responsive import (
    restore_splitter_geometry,
    splitter_ratios_from_sizes,
    splitter_sizes_from_ratios,
)
from ht_coach_app.views.main_window import MainWindow
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.views.squad_page import SquadPage
from ht_coach_app.widgets.formation_board.formation_board import FormationBoard
from tests.test_match_collapsible_sections import rich_match_result
from tests.test_weekly_training_planner import show_weekly_tab


SUPPORTED_SIZES = [
    (1280, 720),
    (1366, 768),
    (1440, 900),
    (1600, 900),
    (1920, 1080),
]


class ResponsiveLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def show_page(self, page, width, height):
        page.resize(width, height)
        page.show()
        QApplication.processEvents()
        QTest.qWait(30)
        QApplication.processEvents()

    def settle_geometry(self, milliseconds=120):
        QApplication.processEvents()
        QTest.qWait(milliseconds)
        QApplication.processEvents()

    def match_page_from_window(self, window):
        for index in range(window.stacked_pages.count()):
            widget = window.stacked_pages.widget(index)
            if isinstance(widget, MatchPage):
                return widget
        self.fail("MainWindow did not create a MatchPage")

    def sections(self, page):
        return {
            section.state_key: section
            for section in page.findChildren(CollapsibleSection)
        }

    def assert_pitch_is_readable(self, board):
        self.assertIsNotNone(board)
        self.assertFalse(board.pitch.isHidden())
        self.assertGreaterEqual(board.pitch.width(), 260)
        self.assertGreaterEqual(board.pitch.height(), 360)
        field = board.pitch.pitch_rect()
        self.assertGreater(field.width(), 160)
        self.assertGreater(field.height(), 250)
        self.assertAlmostEqual(
            field.width() / field.height(),
            68 / 105,
            delta=0.08,
        )

    def test_splitter_proportions_are_ratio_based(self):
        self.assertEqual(splitter_sizes_from_ratios([3, 1]), [750, 250])
        self.assertEqual(
            splitter_sizes_from_ratios([0.72, 0.28]),
            [720, 280],
        )
        self.assertEqual(splitter_ratios_from_sizes([900, 300]), [0.75, 0.25])

    def test_splitter_restore_uses_raw_sizes_only_for_same_width(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page, 1600, 900)
        board = page.findChild(FormationBoard)
        board.splitter.setSizes([900, 300])
        QApplication.processEvents()

        restore_splitter_geometry(
            board.splitter,
            sizes=[900, 300],
            ratios=[0.75, 0.25],
            source_width=1366,
            target_width=1366,
        )
        QApplication.processEvents()
        same_width_sizes = board.splitter.sizes()
        self.assertAlmostEqual(
            same_width_sizes[0] / max(sum(same_width_sizes), 1),
            0.75,
            delta=0.08,
        )

        restore_splitter_geometry(
            board.splitter,
            sizes=[900, 300],
            ratios=[0.75, 0.25],
            source_width=1600,
            target_width=1280,
        )
        QApplication.processEvents()
        resized_width_sizes = board.splitter.sizes()
        self.assertAlmostEqual(
            resized_width_sizes[0] / max(sum(resized_width_sizes), 1),
            0.75,
            delta=0.08,
        )

    def test_match_layout_survives_supported_restored_sizes(self):
        for width, height in SUPPORTED_SIZES:
            with self.subTest(size=(width, height)):
                page = MatchPage()
                page.show_results(rich_match_result())
                sections = {
                    section.state_key: section
                    for section in page.findChildren(CollapsibleSection)
                }
                for section in sections.values():
                    section.set_expanded(False)
                self.show_page(page, width, height)

                ordered = [
                    sections["decision_lab"],
                    sections["match_intelligence"],
                    sections["rating_calibration"],
                    sections["match_analysis"],
                ]
                for index in range(len(ordered) - 1):
                    bottom = ordered[index].mapTo(
                        page,
                        ordered[index].rect().bottomLeft(),
                    ).y()
                    next_top = ordered[index + 1].mapTo(
                        page,
                        ordered[index + 1].rect().topLeft(),
                    ).y()
                    self.assertLessEqual(next_top - bottom, 12)

                workspace = page.findChild(QTabWidget, "matchResultTabs")
                self.assertIsNotNone(workspace)
                self.assertFalse(workspace.isHidden())
                self.assertGreater(workspace.height(), 300)
                board = page.findChild(FormationBoard)
                self.assert_pitch_is_readable(board)

    def test_match_resize_cycle_preserves_workspace_and_scroll(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page, 1366, 768)
        scroll = page.scroll_area.verticalScrollBar()
        scroll.setValue(120)
        before_ratio = (
            scroll.value() / scroll.maximum()
            if scroll.maximum() > 0
            else 0.0
        )

        for width, height in [
            (1920, 1080),
            (1280, 720),
            (1600, 900),
            (1366, 768),
        ]:
            page.resize(width, height)
            QApplication.processEvents()
            self.assert_pitch_is_readable(page.findChild(FormationBoard))
            self.assertFalse(page.findChild(QTabWidget, "matchResultTabs").isHidden())

        self.assertGreaterEqual(scroll.value(), 0)
        self.assertLessEqual(scroll.value(), scroll.maximum())
        if scroll.maximum() > 0:
            self.assertAlmostEqual(
                scroll.value() / scroll.maximum(),
                before_ratio,
                delta=0.35,
            )

    def test_match_restored_window_state_sequences_keep_sections_readable(self):
        for width, height in [(1280, 720), (1366, 768), (1440, 900), (1600, 900)]:
            with self.subTest(size=(width, height)):
                page = MatchPage()
                page.show_results(rich_match_result())
                self.show_page(page, width, height)
                sections = {
                    section.state_key: section
                    for section in page.findChildren(CollapsibleSection)
                }

                for key in (
                    "decision_lab",
                    "match_intelligence",
                    "rating_calibration",
                    "match_analysis",
                ):
                    sections[key].set_expanded(True)
                    QApplication.processEvents()
                    page.showMaximized()
                    QApplication.processEvents()
                    page.showNormal()
                    page.resize(width, height)
                    QApplication.processEvents()
                    QTest.qWait(20)
                    QApplication.processEvents()

                    body = sections[key].body_widget()
                    self.assertFalse(body.isHidden())
                    self.assertGreater(body.height(), 0)
                    self.assertGreater(body.sizeHint().height(), 0)
                    self.assert_pitch_is_readable(page.findChild(FormationBoard))

    def test_match_scroll_restore_clamps_and_keeps_ratio_after_restore_resize(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page, 1366, 620)
        for section in page.findChildren(CollapsibleSection):
            section.set_expanded(True)
        QApplication.processEvents()
        QTest.qWait(20)
        QApplication.processEvents()

        scroll = page.scroll_area.verticalScrollBar()
        if scroll.maximum() <= 0:
            self.skipTest("Offscreen backend did not produce vertical overflow")
        scroll.setValue(scroll.maximum() // 2)
        viewport_state = page._capture_viewport_state()

        page.resize(1280, 720)
        QApplication.processEvents()
        page._restore_viewport_state(viewport_state, page._result_tabs)
        QTest.qWait(30)
        QApplication.processEvents()

        self.assertGreaterEqual(scroll.value(), 0)
        self.assertLessEqual(scroll.value(), scroll.maximum())
        if scroll.maximum() > 0:
            self.assertAlmostEqual(
                scroll.value() / scroll.maximum(),
                viewport_state["vertical_scroll_ratio"],
                delta=0.25,
            )

    def test_match_deferred_geometry_refresh_ignores_stale_requests(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page, 1366, 768)
        before = page._geometry_refresh_revision

        page._schedule_deferred_geometry_refresh()
        page._schedule_deferred_geometry_refresh()
        QTest.qWait(40)
        QApplication.processEvents()

        self.assertEqual(page._geometry_refresh_revision, before + 2)
        self.assert_pitch_is_readable(page.findChild(FormationBoard))

    def test_match_collapsed_and_reexpanded_bodies_restore_positive_height(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page, 1366, 768)
        sections = page.findChildren(CollapsibleSection)

        for section in sections:
            section.set_expanded(False)
        QApplication.processEvents()
        collapsed_heights = [
            section.body_host.height()
            for section in sections
        ]
        self.assertTrue(all(height <= 1 for height in collapsed_heights))

        for section in sections:
            section.set_expanded(True)
        QApplication.processEvents()
        QTest.qWait(30)
        QApplication.processEvents()
        expanded_heights = [
            section.body_widget().height()
            for section in sections
        ]
        self.assertTrue(all(height > 0 for height in expanded_heights))

    def test_match_direct_restored_launch_stabilizes_without_manual_toggle(self):
        window = MainWindow()
        page = self.match_page_from_window(window)
        toggle_events = []
        page.match_section_toggled.connect(
            lambda key, expanded: toggle_events.append((key, expanded))
        )
        page.show_results(rich_match_result(), restored=True)

        window.resize(1366, 768)
        window.show()
        window.navigation_controller.navigate_to("match")
        self.settle_geometry()

        self.assertEqual(toggle_events, [])
        self.assertEqual(page.match_geometry_invariant_failures(), [])
        report = page.last_initial_geometry_report()
        self.assertLessEqual(report.get("passes", 0), page.INITIAL_GEOMETRY_MAX_PASSES)

    def test_match_hidden_page_activation_stabilizes_restored_geometry(self):
        window = MainWindow()
        page = self.match_page_from_window(window)
        page.show_results(rich_match_result(), restored=True)

        window.resize(1366, 768)
        window.show()
        window.navigation_controller.navigate_to("dashboard")
        self.settle_geometry(40)
        self.assertFalse(page.isVisible())

        window.navigation_controller.navigate_to("match")
        self.settle_geometry()

        self.assertTrue(page.isVisible())
        self.assertEqual(page.match_geometry_invariant_failures(), [])
        self.assertEqual(
            page.last_initial_geometry_report().get("viewport"),
            page._current_visible_viewport(),
        )

    def test_match_initial_section_states_preserve_geometry_without_toggle(self):
        state_sets = [
            {
                "decision_lab": False,
                "match_intelligence": False,
                "rating_calibration": False,
                "match_analysis": False,
            },
            {"decision_lab": True},
            {"match_intelligence": True},
            {"rating_calibration": True},
            {"match_analysis": True},
            {
                "decision_lab": True,
                "match_intelligence": False,
                "rating_calibration": True,
                "match_analysis": False,
            },
        ]

        for states in state_sets:
            with self.subTest(states=states):
                page = MatchPage()
                page.apply_settings(
                    MatchWorkspaceSettings(match_section_states=states)
                )
                toggle_events = []
                page.match_section_toggled.connect(
                    lambda key, expanded: toggle_events.append((key, expanded))
                )
                page.show_results(rich_match_result(), restored=True)
                self.show_page(page, 1366, 768)
                page.request_initial_geometry_stabilization("test")
                self.settle_geometry()

                effective = page.match_section_states()
                for key, default in page.MATCH_SECTION_DEFAULTS.items():
                    self.assertEqual(
                        effective[key],
                        states.get(key, default),
                    )
                self.assertEqual(toggle_events, [])
                self.assertEqual(page.match_geometry_invariant_failures(), [])

    def test_match_headers_reflow_without_overlap_on_initial_restored_width(self):
        page = MatchPage()
        page.show_results(rich_match_result(), restored=True)
        self.show_page(page, 1280, 720)
        page.request_initial_geometry_stabilization("test_header_reflow")
        self.settle_geometry()

        for section in self.sections(page).values():
            with self.subTest(section=section.state_key):
                self.assertGreaterEqual(
                    section.header_button.height() + 1,
                    section.header_button.minimumSizeHint().height(),
                )
                self.assertLess(
                    section.title_label.geometry().bottom(),
                    section.summary_label.geometry().top(),
                )

        page.resize(1600, 900)
        self.settle_geometry()
        self.assertEqual(page.match_geometry_invariant_failures(), [])

    def test_match_startup_stale_callbacks_do_not_apply_old_viewport(self):
        page = MatchPage()
        page.show_results(rich_match_result(), restored=True)
        self.show_page(page, 1366, 768)

        page.request_initial_geometry_stabilization("test_old_viewport")
        page.resize(1600, 900)
        QApplication.processEvents()
        page.request_initial_geometry_stabilization("test_new_viewport")
        self.settle_geometry()

        self.assertEqual(page.match_geometry_invariant_failures(), [])
        self.assertEqual(
            page.last_initial_geometry_report().get("viewport"),
            page._current_visible_viewport(),
        )

    def test_match_return_after_navigate_away_uses_current_viewport(self):
        window = MainWindow()
        page = self.match_page_from_window(window)
        page.show_results(rich_match_result(), restored=True)
        window.resize(1366, 768)
        window.show()

        window.navigation_controller.navigate_to("match")
        page.request_initial_geometry_stabilization("test_navigate_away")
        window.navigation_controller.navigate_to("dashboard")
        self.settle_geometry(80)
        window.navigation_controller.navigate_to("match")
        self.settle_geometry()

        self.assertEqual(page.match_geometry_invariant_failures(), [])
        self.assertEqual(
            page.last_initial_geometry_report().get("viewport"),
            page._current_visible_viewport(),
        )

    def test_match_maximize_restore_cycle_keeps_pitch_visible(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page, 1280, 720)

        page.showMaximized()
        QApplication.processEvents()
        self.assert_pitch_is_readable(page.findChild(FormationBoard))

        page.showNormal()
        page.resize(1280, 720)
        QApplication.processEvents()
        self.assert_pitch_is_readable(page.findChild(FormationBoard))

    def test_squad_and_weekly_workspaces_resize_without_pitch_clipping(self):
        for tab_key in ("ideal", "weekly_planner"):
            with self.subTest(tab=tab_key):
                page = SquadPage()
                if tab_key == "weekly_planner":
                    show_weekly_tab(page)
                else:
                    page.set_selected_tab("ideal")

                for width, height in [(1280, 720), (1600, 900), (1920, 1080)]:
                    self.show_page(page, width, height)
                    board = (
                        page.weekly_plan_board
                        if tab_key == "weekly_planner"
                        else page.ideal_board
                    )
                    self.assert_pitch_is_readable(board)
