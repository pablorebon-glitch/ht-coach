import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ht_coach_app.core.order_formatting import format_order
from ht_coach_app.core.position_formatting import (
    format_position,
    format_position_abbreviation,
)
from ht_coach_app.core.side_formatting import format_side
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    format_recommended_lineup,
)
from ht_coach_app.reasoning.models import (
    ConfidenceAssessment,
    DecisionLabResult,
    DecisionReason,
    RecommendedDecision,
)
from ht_coach_app.widgets.formation_board.formation_layouts import (
    get_formation_layout,
    supported_formation_layouts,
)
from models.formations import FORMATION_BY_NAME
from models.position import Position


SUPPORTED_FORMATIONS = [
    "2-5-3",
    "3-4-3",
    "3-5-2",
    "4-3-3",
    "4-4-2",
    "4-5-1",
    "5-2-3",
    "5-3-2",
    "5-4-1",
]


def formation_result(name="3-5-2", recommended=True):
    lineup = [
        LineupPlayerResult(
            number=index + 1,
            position=slot.position_label,
            side=slot.side,
            order="Towards Wing" if slot.side != "CENTER" else "Normal",
            order_side=slot.side if slot.side != "CENTER" else "",
            player_name=f"{slot.side_label} {slot.position_label} {index + 1}",
        )
        for index, slot in enumerate(get_formation_layout(name))
    ]
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


class FormationLayoutTest(unittest.TestCase):
    def test_every_supported_formation_has_eleven_deterministic_slots(self):
        self.assertEqual(
            sorted(supported_formation_layouts()),
            sorted(SUPPORTED_FORMATIONS),
        )

        for name in SUPPORTED_FORMATIONS:
            first = get_formation_layout(name)
            second = get_formation_layout(name)

            self.assertEqual(first, second)
            self.assertEqual(len(first), 11)
            self.assertEqual(
                len({slot.slot_id for slot in first}),
                11,
            )

            for slot in first:
                self.assertGreaterEqual(slot.normalized_x, 0.0)
                self.assertLessEqual(slot.normalized_x, 1.0)
                self.assertGreaterEqual(slot.normalized_y, 0.0)
                self.assertLessEqual(slot.normalized_y, 1.0)

    def test_layouts_match_central_formation_catalog_counts(self):
        for name in SUPPORTED_FORMATIONS:
            layout = get_formation_layout(name)
            counts = {}

            for slot in layout:
                counts[slot.position] = counts.get(slot.position, 0) + 1

            expected = {
                position.value: amount
                for position, amount
                in FORMATION_BY_NAME[name].positions.items()
            }
            self.assertEqual(counts, expected)

    def test_pitch_orientation_and_left_right_semantics(self):
        for name in SUPPORTED_FORMATIONS:
            layout = get_formation_layout(name)
            goalkeeper_y = min(
                slot.normalized_y
                for slot in layout
                if slot.line == "goalkeeper"
            )
            defense_y = min(
                slot.normalized_y
                for slot in layout
                if slot.line == "defense"
            )
            midfield_y = min(
                slot.normalized_y
                for slot in layout
                if slot.line == "midfield"
            )
            forward_y = min(
                slot.normalized_y
                for slot in layout
                if slot.line == "forward"
            )

            self.assertLess(goalkeeper_y, defense_y)
            self.assertLess(defense_y, midfield_y)
            self.assertLess(midfield_y, forward_y)

            for position in {slot.position for slot in layout}:
                left = [
                    slot for slot in layout
                    if slot.position == position and slot.side == "LEFT"
                ]
                right = [
                    slot for slot in layout
                    if slot.position == position and slot.side == "RIGHT"
                ]

                if left and right:
                    self.assertLess(
                        left[0].normalized_x,
                        right[0].normalized_x,
                    )


class FormationBoardMapperTest(unittest.TestCase):
    def test_lineup_maps_to_board_slots_with_user_facing_labels(self):
        board = FormationBoardMapper().to_board(
            formation_result("3-5-2")
        )

        self.assertEqual(board.formation_name, "3-5-2")
        self.assertEqual(len(board.slots), 11)
        self.assertTrue(
            all(slot.player is not None for slot in board.slots)
        )

        goalkeeper = next(
            slot.player
            for slot in board.slots
            if slot.position == Position.GOALKEEPER.value
        )
        self.assertEqual(goalkeeper.position_label, "Goalkeeper (GK)")
        self.assertEqual(goalkeeper.position_abbreviation, "GK")
        self.assertEqual(goalkeeper.side_label, "Center")
        self.assertEqual(goalkeeper.order_label, "Normal")

        winger = next(
            slot.player
            for slot in board.slots
            if slot.side == "LEFT" and slot.player.order_side
        )
        self.assertEqual(winger.order_side_label, "Left")
        self.assertEqual(winger.order_label, "Towards Wing")

    def test_missing_optional_lineup_data_leaves_empty_slots(self):
        result = formation_result("4-4-2")
        result = FormationAnalysisResult(
            **{
                **result.__dict__,
                "lineup": result.lineup[:2],
            }
        )

        board = FormationBoardMapper().to_board(result, restored=True)

        self.assertEqual(len(board.slots), 11)
        self.assertEqual(
            len([slot for slot in board.slots if slot.player is None]),
            9,
        )
        self.assertTrue(board.restored)

    def test_long_names_truncate_and_stable_id_is_deterministic(self):
        result = formation_result("3-5-2")
        long_player = LineupPlayerResult(
            number=99,
            position="Goalkeeper (GK)",
            side="CENTER",
            order="Normal",
            order_side="",
            player_name="A Very Long Player Name For The Board",
        )
        result = FormationAnalysisResult(
            **{
                **result.__dict__,
                "lineup": [long_player],
            }
        )
        mapper = FormationBoardMapper()
        first = mapper.to_board(result)
        second = mapper.to_board(result)
        player = first.slots[0].player

        self.assertEqual(player.display_name, "A Very Long Pla...")
        self.assertEqual(
            player.player_name,
            "A Very Long Player Name For The Board",
        )
        self.assertEqual(
            player.player_id,
            second.slots[0].player.player_id,
        )

    def test_selection_and_clear_selection_are_immutable(self):
        mapper = FormationBoardMapper()
        board = mapper.to_board(formation_result("3-5-2"))
        player_id = board.slots[0].player.player_id

        selected = mapper.select_player(board, player_id)
        cleared = mapper.clear_selection(selected)

        self.assertEqual(board.selected_player_id, "")
        self.assertEqual(selected.selected_player_id, player_id)
        self.assertTrue(selected.slots[0].player.is_selected)
        self.assertEqual(cleared.selected_player_id, "")
        self.assertFalse(cleared.slots[0].player.is_selected)

    def test_all_nine_formations_map_without_engine_calls(self):
        mapper = FormationBoardMapper()

        for name in SUPPORTED_FORMATIONS:
            board = mapper.to_board(formation_result(name))
            self.assertEqual(board.formation_name, name)
            self.assertEqual(len(board.slots), 11)


class FormationBoardFormattingTest(unittest.TestCase):
    def test_centralized_labels_are_used(self):
        self.assertEqual(
            format_position(Position.INNER_MIDFIELDER),
            "Inner Midfielder (IM)",
        )
        self.assertEqual(
            format_position_abbreviation("Central Defender (CD)"),
            "CD",
        )
        self.assertEqual(format_side("RIGHT"), "Right")
        self.assertEqual(format_order("TOWARDS_MIDDLE"), "Towards Middle")

    def test_copy_lineup_uses_pitch_order(self):
        result = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[formation_result("4-4-2")],
        )
        copied = format_recommended_lineup(result).splitlines()

        self.assertIn("Goalkeeper", copied[2])
        self.assertLess(
            copied.index(
                next(line for line in copied if "Wing Back" in line)
            ),
            copied.index(
                next(line for line in copied if "Inner Midfielder" in line)
            ),
        )


try:
    from PySide6.QtWidgets import QApplication, QLabel, QTabWidget

    from ht_coach_app.views.match_page import MatchPage
    from ht_coach_app.widgets.formation_board.formation_board import (
        FormationBoard,
    )
    from ht_coach_app.widgets.formation_board.player_card import PlayerCard
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QApplication = None
    FormationBoard = None
    MatchPage = None
    PlayerCard = None
    QTabWidget = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class FormationBoardQtSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_board_constructs_selects_and_clears_player(self):
        board_widget = FormationBoard()
        board_model = FormationBoardMapper().to_board(
            formation_result("3-5-2")
        )
        board_widget.set_boards([board_model])
        board_widget.resize(900, 700)

        cards = board_widget.findChildren(PlayerCard)
        self.assertEqual(len(cards), 11)

        first_id = board_widget.current_board().slots[0].player.player_id
        board_widget.select_player(first_id)
        self.assertEqual(
            board_widget.current_board().selected_player_id,
            first_id,
        )

        board_widget.clear_selection()
        self.assertEqual(
            board_widget.current_board().selected_player_id,
            "",
        )

    def test_match_page_uses_board_comparison_and_detailed_xi_tabs(self):
        page = MatchPage()
        result = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[
                formation_result("3-5-2", recommended=True),
                formation_result("4-5-1", recommended=False),
            ],
            analyzed_formations=["3-5-2", "4-5-1"],
            players_csv_filename="players.csv",
            completed_at="2026-07-16 12:00:00",
        )

        page.show_results(result)
        tabs = page.findChild(QTabWidget, "matchResultTabs")

        self.assertIsNotNone(tabs)
        self.assertEqual(tabs.tabText(0), "Formation Board")
        self.assertEqual(tabs.tabText(1), "Comparison")
        self.assertEqual(tabs.tabText(2), "Detailed XI")
        self.assertEqual(tabs.currentIndex(), 0)

    def test_decision_lab_remains_visible_above_result_tabs(self):
        page = MatchPage()
        result = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[
                formation_result("3-5-2", recommended=True),
                formation_result("4-5-1", recommended=False),
            ],
            analyzed_formations=["3-5-2", "4-5-1"],
            players_csv_filename="players.csv",
            completed_at="2026-07-16 12:00:00",
            decision_lab=DecisionLabResult(
                recommended_formation=RecommendedDecision(
                    formation="3-5-2",
                    tactic="Pressing",
                    win_probability=0.55,
                    confidence="HIGH",
                ),
                headline="3-5-2 is recommended",
                summary="Decision Lab summary",
                confidence=ConfidenceAssessment(
                    level="HIGH",
                    score=0.9,
                    explanation="Clear advantage.",
                ),
                confidence_score=0.9,
                reasons=[
                    DecisionReason(
                        code="win",
                        title="Highest win probability",
                        description="Best result among analyzed formations.",
                        importance="high",
                    )
                ],
            ),
        )

        page.show_results(result)
        widgets = [
            page.results_layout.itemAt(index).widget()
            for index in range(page.results_layout.count())
            if page.results_layout.itemAt(index).widget() is not None
        ]
        tabs = page.findChild(QTabWidget, "matchResultTabs")
        tabs_index = widgets.index(tabs)
        labels_before_tabs = [
            label.text()
            for widget in widgets[:tabs_index]
            for label in widget.findChildren(QLabel)
        ]

        self.assertIn("Decision Lab", labels_before_tabs)
        self.assertEqual(tabs.tabText(0), "Formation Board")


if __name__ == "__main__":
    unittest.main()
