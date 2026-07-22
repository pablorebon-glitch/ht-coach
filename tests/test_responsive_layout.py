import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from ht_coach_app.ui.design_system.collapsible_section import CollapsibleSection
from ht_coach_app.ui.responsive import (
    splitter_sizes_from_ratios,
)
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
        before = scroll.value()

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
        self.assertLessEqual(abs(scroll.value() - before), 160)

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
