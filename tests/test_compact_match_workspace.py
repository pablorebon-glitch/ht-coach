import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea, QSplitter

from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
)
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.widgets.formation_board.formation_board import FormationBoard
from ht_coach_app.widgets.formation_board.layout_metrics import PITCH_ASPECT_RATIO
from ht_coach_app.widgets.formation_board.layout_metrics import BOARD_MINIMUM_HEIGHT
from ht_coach_app.widgets.formation_board.player_card import PlayerCard
from ht_coach_app.widgets.formation_board.pitch_widget import PitchWidget
from ht_coach_app.widgets.formation_board.formation_layouts import get_formation_layout


def formation_result(name="3-5-2", recommended=True, long_name=False):
    lineup = []
    for index, slot in enumerate(get_formation_layout(name)):
        player_name = f"Player {index + 1}"
        if long_name and index == 0:
            player_name = "A Player Name That Is Far Too Long For The Card"
        lineup.append(
            LineupPlayerResult(
                number=index + 1,
                position=slot.position_label,
                side=slot.side,
                order="Normal",
                order_side="",
                player_name=player_name,
            )
        )

    return FormationAnalysisResult(
        formation_name=name,
        recommended_tactic="Pressing",
        tactic_level=7.25,
        win_probability=0.55,
        draw_probability=0.25,
        loss_probability=0.20,
        possession=0.61,
        expected_goals=2.1,
        opponent_expected_goals=1.2,
        lineup=lineup,
        is_recommended=recommended,
    )


def match_result():
    return MatchAnalysisResult(
        player_count=22,
        opponent_name="Rival FC",
        formations=[
            formation_result("3-5-2", recommended=True),
            formation_result("4-5-1", recommended=False),
        ],
        players_csv_filename="players.csv",
        analyzed_formations=["3-5-2", "4-5-1"],
        completed_at="2026-07-17 12:00:00",
    )


class CompactMatchWorkspaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_analysis_form_collapses_and_reopens_without_rerun(self):
        page = MatchPage()
        analyze_requests = []
        page.analyze_requested.connect(lambda: analyze_requests.append(True))

        self.assertTrue(page.analysis_inputs_expanded())
        page.show_results(match_result())
        self.assertFalse(page.analysis_inputs_expanded())

        page.expand_analysis_inputs()
        self.assertTrue(page.analysis_inputs_expanded())
        self.assertEqual(analyze_requests, [])
        self.assertEqual(page.current_state(), "success")

        page.collapse_analysis_inputs()
        self.assertFalse(page.analysis_inputs_expanded())
        self.assertEqual(analyze_requests, [])
        self.assertEqual(page.current_state(), "success")

    def test_analysis_setup_values_survive_toggle_and_page_is_scrollable(self):
        page = MatchPage()
        page.set_players_csv_path("C:/data/players.csv")
        page.set_opponents(["Rival FC"], selected_name="Rival FC")
        page.show_results(match_result())

        scroll = page.findChild(QScrollArea, "matchPageScroll")
        self.assertIsNotNone(scroll)
        self.assertTrue(scroll.widgetResizable())
        self.assertFalse(page.analysis_inputs_expanded())

        page.expand_analysis_inputs()
        self.assertEqual(page.players_csv_path(), "C:/data/players.csv")
        self.assertEqual(page.selected_opponent_name(), "Rival FC")
        page.collapse_analysis_inputs()
        self.assertEqual(page.current_state(), "success")

    def test_pitch_keeps_aspect_ratio_and_contains_both_goals(self):
        pitch = PitchWidget()
        pitch.resize(760, 480)
        rect = pitch.pitch_rect()
        top_goal, bottom_goal = pitch.goal_rects()

        self.assertAlmostEqual(
            rect.width() / rect.height(),
            PITCH_ASPECT_RATIO,
            places=3,
        )
        self.assertGreaterEqual(top_goal.top(), 0)
        self.assertLessEqual(bottom_goal.bottom(), pitch.height())
        self.assertLess(top_goal.top(), rect.top())
        self.assertGreater(bottom_goal.bottom(), rect.bottom())
        geometry = pitch.geometry_model()
        self.assertTrue(geometry.external_bounds.contains(top_goal))
        self.assertTrue(geometry.external_bounds.contains(bottom_goal))

    def test_corner_arcs_are_anchored_to_pitch_corners_and_curve_inward(self):
        pitch = PitchWidget()
        pitch.resize(760, 620)
        rect = pitch.pitch_rect()
        arcs = {
            arc.name: arc
            for arc in pitch.corner_arcs()
        }

        self.assertEqual(len(arcs), 4)
        self.assertEqual(arcs["top_left"].anchor, rect.topLeft())
        self.assertEqual(arcs["top_right"].anchor, rect.topRight())
        self.assertEqual(arcs["bottom_left"].anchor, rect.bottomLeft())
        self.assertEqual(arcs["bottom_right"].anchor, rect.bottomRight())
        self.assertGreater(arcs["top_left"].rect.right(), rect.left())
        self.assertGreater(arcs["top_left"].rect.bottom(), rect.top())
        self.assertLess(arcs["top_right"].rect.left(), rect.right())
        self.assertGreater(arcs["top_right"].rect.bottom(), rect.top())
        self.assertGreater(arcs["bottom_left"].rect.right(), rect.left())
        self.assertLess(arcs["bottom_left"].rect.top(), rect.bottom())
        self.assertLess(arcs["bottom_right"].rect.left(), rect.right())
        self.assertLess(arcs["bottom_right"].rect.top(), rect.bottom())

    def test_all_cards_stay_inside_pitch_without_overlap(self):
        pitch = PitchWidget()
        board = FormationBoardMapper().to_board(formation_result("3-5-2"))
        pitch.resize(260, 380)
        pitch.set_board(board)
        QApplication.processEvents()

        field = pitch.pitch_rect().toAlignedRect()
        geometries = pitch.card_geometries()
        self.assertEqual(len(geometries), 11)
        self.assertTrue(all(field.contains(geometry) for geometry in geometries))

        for index, first in enumerate(geometries):
            for second in geometries[index + 1 :]:
                self.assertFalse(first.intersects(second))

    def test_long_names_are_elided_and_keep_full_tooltip(self):
        pitch = PitchWidget()
        board = FormationBoardMapper().to_board(
            formation_result("3-5-2", long_name=True)
        )
        pitch.resize(500, 430)
        pitch.set_board(board)
        QApplication.processEvents()

        card = next(
            item
            for item in pitch.findChildren(PlayerCard)
            if item.player.player_name.startswith("A Player Name")
        )
        self.assertIn("...", card.text().replace("\u2026", "..."))
        self.assertIn(card.player.player_name, card.toolTip())

    def test_board_uses_horizontal_splitter_and_internal_inspector_scroll(self):
        board = FormationBoard()
        splitter = board.findChild(QSplitter, "formationWorkspaceSplitter")
        inspector_scroll = board.findChild(QScrollArea, "playerInspectorScroll")

        self.assertIsNotNone(splitter)
        self.assertEqual(splitter.orientation(), Qt.Horizontal)
        self.assertEqual(splitter.count(), 2)
        self.assertGreaterEqual(board.minimumHeight(), BOARD_MINIMUM_HEIGHT)
        self.assertIsNotNone(inspector_scroll)
        self.assertTrue(inspector_scroll.widgetResizable())
        self.assertEqual(
            inspector_scroll.horizontalScrollBarPolicy(),
            Qt.ScrollBarAlwaysOff,
        )

    def test_selection_and_formation_switch_do_not_change_pitch_geometry(self):
        first = FormationBoardMapper().to_board(formation_result("3-5-2"))
        second = FormationBoardMapper().to_board(
            formation_result("4-5-1", recommended=False)
        )
        board = FormationBoard()
        board.resize(1000, 560)
        board.set_boards([first, second])
        QApplication.processEvents()
        before = board.pitch.pitch_rect()

        board.select_player(first.slots[0].player.player_id)
        board.formation_combo.setCurrentIndex(1)
        QApplication.processEvents()

        self.assertEqual(before, board.pitch.pitch_rect())
        self.assertEqual(board.current_board().selected_player_id, "")

    def test_workspace_resizes_safely_at_supported_desktop_sizes(self):
        page = MatchPage()
        page.show_results(match_result(), restored=True)
        for width, height in (
            (1280, 720),
            (1366, 768),
            (1600, 900),
            (1920, 1080),
        ):
            page.resize(width, height)
            page.show()
            QApplication.processEvents()
            board = page.findChild(FormationBoard)
            self.assertIsNotNone(board)
            self.assertEqual(len(board.pitch.findChildren(PlayerCard)), 11)
            self.assertTrue(board.pitch.pitch_rect().isValid())
        page.close()

    def test_compact_summary_removes_low_value_fields_and_actions(self):
        page = MatchPage()
        page.show_results(match_result())

        labels = [
            label.text()
            for label in page.findChildren(QLabel)
        ]
        buttons = [
            button.text()
            for button in page.findChildren(QPushButton)
        ]

        self.assertIn("Opponent: Rival FC", labels)
        self.assertIn("Formations: 2", labels)
        self.assertNotIn("CSV  players.csv", labels)
        self.assertFalse(any("players.csv" in label for label in labels))
        self.assertFalse(any("Players  22" in label for label in labels))
        self.assertFalse(any("2026-07-17" in label for label in labels))
        self.assertNotIn("Copy summary", buttons)
        self.assertNotIn("Copy Decision Lab", buttons)
        self.assertNotIn("Copy lineup", buttons)
        self.assertNotIn("Edit analysis", buttons)


if __name__ == "__main__":
    unittest.main()
