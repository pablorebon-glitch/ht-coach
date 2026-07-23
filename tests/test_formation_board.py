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
from ht_coach_app.workspace.workspace_models import (
    WorkspaceModification,
    WorkspaceState,
)
from ht_coach_app.widgets.formation_board.formation_layouts import (
    get_formation_layout,
    supported_formation_layouts,
)
from ht_coach_app.widgets.formation_board.orientation import (
    mirror_normalized_x,
    screen_x_for_tactical_side,
    tactical_side_to_visual_side,
)
from models.player import Player
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


def order_sync_result(name="2-5-3", recommended=True):
    lineup = [
        LineupPlayerResult(1, "Goalkeeper (GK)", "CENTER", "Normal", "", "Goalkeeper One"),
        LineupPlayerResult(2, "Central Defender (CD)", "LEFT", "Offensive", "", "Roberto Jubileu"),
        LineupPlayerResult(3, "Central Defender (CD)", "RIGHT", "Offensive", "", "Mauricio Gustavo Bassedas"),
        LineupPlayerResult(4, "Winger (W)", "LEFT", "Offensive", "", "Nahuel Pulian"),
        LineupPlayerResult(5, "Winger (W)", "RIGHT", "Offensive", "", "Emiliano Jose Rodriguez"),
        LineupPlayerResult(6, "Inner Midfielder (IM)", "LEFT", "Offensive", "", "Pierre-Jean Delion"),
        LineupPlayerResult(7, "Inner Midfielder (IM)", "CENTER", "Offensive", "", "Fabian Abbiendi"),
        LineupPlayerResult(8, "Inner Midfielder (IM)", "RIGHT", "Offensive", "", "Diego Garcia de Paredes"),
        LineupPlayerResult(9, "Forward (F)", "LEFT", "Normal", "", "Nestor Agusevich"),
        LineupPlayerResult(10, "Forward (F)", "CENTER", "Towards Wing", "LEFT", "Michael Rushton"),
        LineupPlayerResult(11, "Forward (F)", "RIGHT", "Normal", "", "David Schiller"),
    ]
    return FormationAnalysisResult(
        formation_name=name,
        recommended_tactic="Normal",
        tactic_level=0,
        win_probability=0.55,
        draw_probability=0.25,
        loss_probability=0.20,
        possession=0.61,
        expected_goals=2.1,
        opponent_expected_goals=1.2,
        lineup=lineup,
        is_recommended=recommended,
    )


def all_normal_result():
    result = order_sync_result()
    return FormationAnalysisResult(
        **{
            **result.__dict__,
            "lineup": [
                LineupPlayerResult(
                    player.number,
                    player.position,
                    player.side,
                    "Normal",
                    "",
                    player.player_name,
                )
                for player in result.lineup
            ],
        }
    )


def order_sync_roster():
    return [
        Player(
            name=player.player_name,
            age=25,
            days=0,
            speciality="",
            form=7,
            stamina=7,
            goalkeeper=1,
            defending=8,
            playmaking=8,
            winger=8,
            passing=8,
            scoring=8,
            set_pieces=5,
            experience=5,
            leadership=5,
            tsi=1000,
            salary=1000,
        )
        for player in order_sync_result().lineup
    ]


def lineup_order_map(formation):
    return {
        (
            player.player_name,
            player.position,
            player.side,
        ): (player.order, player.order_side or "")
        for player in formation.lineup
    }


def board_order_map(board):
    return {
        (
            slot.player.player_name,
            slot.player.position_label,
            slot.player.side,
        ): (slot.player.order_label, slot.player.order_side)
        for slot in board.slots
        if slot.player is not None
    }


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
                    self.assertGreater(
                        left[0].normalized_x,
                        right[0].normalized_x,
                    )

    def test_tactical_left_right_screen_conversion_is_centralized(self):
        self.assertEqual(mirror_normalized_x(0.2), 0.8)
        self.assertEqual(screen_x_for_tactical_side(0.75), 0.25)
        self.assertEqual(tactical_side_to_visual_side("LEFT"), "RIGHT")
        self.assertEqual(tactical_side_to_visual_side("RIGHT"), "LEFT")
        self.assertEqual(tactical_side_to_visual_side("CENTER"), "CENTER")


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

    def test_mapper_preserves_individual_orders_and_order_sides(self):
        result = order_sync_result()

        board = FormationBoardMapper().to_board(result)

        self.assertEqual(board_order_map(board), lineup_order_map(result))
        michael = next(
            slot.player
            for slot in board.slots
            if slot.player is not None
            and slot.player.player_name == "Michael Rushton"
        )
        self.assertEqual(michael.individual_order, "Towards Wing")
        self.assertEqual(michael.order_label, "Towards Wing")
        self.assertEqual(michael.order_side, "LEFT")
        self.assertEqual(michael.order_side_label, "Left")

    def test_directional_order_uses_order_side_sector_without_mutating_field_side(self):
        result = order_sync_result()

        board = FormationBoardMapper().to_board(result)
        michael_slot = next(
            slot
            for slot in board.slots
            if slot.player is not None
            and slot.player.player_name == "Michael Rushton"
        )
        right_forward_slot = next(
            slot
            for slot in board.slots
            if slot.position == Position.FORWARD.value
            and slot.side == "RIGHT"
        )

        self.assertEqual(michael_slot.side, "LEFT")
        self.assertEqual(michael_slot.player.side, "CENTER")
        self.assertEqual(michael_slot.player.order_side, "LEFT")
        self.assertGreater(michael_slot.normalized_x, right_forward_slot.normalized_x)

    def test_right_directional_order_uses_mirrored_tactical_sector(self):
        result = order_sync_result()
        lineup = [
            (
                LineupPlayerResult(
                    player.number,
                    player.position,
                    player.side,
                    player.order,
                    "RIGHT",
                    player.player_name,
                )
                if player.player_name == "Michael Rushton"
                else player
            )
            for player in result.lineup
        ]
        result = FormationAnalysisResult(**{**result.__dict__, "lineup": lineup})

        board = FormationBoardMapper().to_board(result)
        michael_slot = next(
            slot
            for slot in board.slots
            if slot.player is not None
            and slot.player.player_name == "Michael Rushton"
        )
        left_forward_slot = next(
            slot
            for slot in board.slots
            if slot.position == Position.FORWARD.value
            and slot.side == "LEFT"
        )

        self.assertEqual(michael_slot.side, "RIGHT")
        self.assertEqual(michael_slot.player.side, "CENTER")
        self.assertEqual(michael_slot.player.order_side, "RIGHT")
        self.assertLess(michael_slot.normalized_x, left_forward_slot.normalized_x)

    def test_workspace_creation_can_preserve_authoritative_input_orders(self):
        from ht_coach_app.workspace.workspace_service import WorkspaceService

        result = order_sync_result()
        board = FormationBoardMapper().to_board(result)

        state = WorkspaceService().create(
            [board],
            "2-5-3",
            roster_players=order_sync_roster(),
            optimize_orders=False,
        )

        self.assertEqual(
            board_order_map(state.current_board),
            lineup_order_map(result),
        )


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

    def test_bench_and_details_side_panels_collapse_without_destroying_content(self):
        from ht_coach_app.ui.design_system.collapsible_side_panel import (
            CollapsibleSidePanel,
        )

        board_widget = FormationBoard()
        panels = board_widget.findChildren(CollapsibleSidePanel)
        by_key = {panel.state_key: panel for panel in panels}

        self.assertIn("formation_board.bench", by_key)
        self.assertIn("formation_board.details", by_key)

        bench_panel = by_key["formation_board.bench"]
        details_panel = by_key["formation_board.details"]
        bench_content = bench_panel.content_widget()
        details_content = details_panel.content_widget()

        bench_panel.set_expanded(False)
        details_panel.set_expanded(False)
        QApplication.processEvents()

        self.assertLessEqual(bench_panel.maximumWidth(), 40)
        self.assertLessEqual(details_panel.maximumWidth(), 40)
        self.assertIs(bench_panel.content_widget(), bench_content)
        self.assertIs(details_panel.content_widget(), details_content)

        bench_panel.set_expanded(True)
        details_panel.set_expanded(True)
        QApplication.processEvents()

        self.assertFalse(bench_panel.content_host.isHidden())
        self.assertFalse(details_panel.content_host.isHidden())

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
        tabs_index = next(
            index for index, widget in enumerate(widgets)
            if widget.isAncestorOf(tabs)
        )
        labels_before_tabs = [
            label.text()
            for widget in widgets[:tabs_index]
            for label in widget.findChildren(QLabel)
        ]

        self.assertIn("Decision Lab", labels_before_tabs)
        self.assertEqual(tabs.tabText(0), "Formation Board")

    def test_match_page_board_orders_match_detailed_xi_view_models(self):
        page = MatchPage()
        page.set_roster_players(order_sync_roster())
        result = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[order_sync_result()],
            analyzed_formations=["2-5-3"],
            players_csv_filename="players.csv",
            completed_at="2026-07-23 00:00:00",
        )

        page.show_results(result)
        board = page._formation_board_widget.current_board()

        self.assertEqual(
            board_order_map(board),
            lineup_order_map(result.recommended_formation),
        )

    def test_player_cards_render_optimized_offensive_and_directional_orders(self):
        page = MatchPage()
        page.set_roster_players(order_sync_roster())
        result = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[order_sync_result()],
            analyzed_formations=["2-5-3"],
            players_csv_filename="players.csv",
            completed_at="2026-07-23 00:00:00",
        )

        page.show_results(result)
        cards_by_player = {
            card.player.player_name: card
            for card in page._formation_board_widget.findChildren(PlayerCard)
        }

        for player_name in (
            "Roberto Jubileu",
            "Mauricio Gustavo Bassedas",
            "Pierre-Jean Delion",
            "Fabian Abbiendi",
            "Diego Garcia de Paredes",
        ):
            self.assertIn("Offensive", cards_by_player[player_name].text())

        rushton_text = cards_by_player["Michael Rushton"].text()
        self.assertIn("Towards Wing", rushton_text)
        self.assertIn("Left", rushton_text)

    def test_fresh_match_analysis_replaces_stale_board_orders(self):
        page = MatchPage()
        page.set_roster_players(order_sync_roster())
        stale = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[all_normal_result()],
            analyzed_formations=["2-5-3"],
        )
        fresh = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[order_sync_result()],
            analyzed_formations=["2-5-3"],
        )

        page.show_results(stale)
        self.assertNotEqual(
            board_order_map(page._formation_board_widget.current_board()),
            lineup_order_map(fresh.recommended_formation),
        )

        page.show_results(fresh)

        self.assertEqual(
            board_order_map(page._formation_board_widget.current_board()),
            lineup_order_map(fresh.recommended_formation),
        )

    def test_match_result_refresh_preserves_board_order_consistency(self):
        page = MatchPage()
        page.set_roster_players(order_sync_roster())
        result = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[order_sync_result()],
            analyzed_formations=["2-5-3"],
        )

        page.show_results(result)
        page.show_results(result)

        self.assertEqual(
            board_order_map(page._formation_board_widget.current_board()),
            lineup_order_map(result.recommended_formation),
        )

    def test_formation_switch_preserves_each_formation_orders(self):
        first = order_sync_result("2-5-3", recommended=True)
        second = formation_result("4-5-1", recommended=False)
        result = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[first, second],
            analyzed_formations=["2-5-3", "4-5-1"],
        )
        page = MatchPage()

        page.show_results(result)
        page._formation_board_widget.formation_combo.setCurrentIndex(1)

        self.assertEqual(
            board_order_map(page._formation_board_widget.current_board()),
            lineup_order_map(second),
        )

    def test_recalculated_manual_workspace_keeps_table_and_board_synchronized(self):
        result = order_sync_result()
        board = FormationBoardMapper().to_board(result)
        manual_board = FormationBoardMapper().to_board(result)
        state = WorkspaceState(
            original_boards={"2-5-3": board},
            workspace_boards={"2-5-3": manual_board},
            current_formation_name="2-5-3",
            history=(
                WorkspaceModification(
                    formation_name="2-5-3",
                    slot_id="manual",
                    role="Forward",
                    original_player_name="Nestor Agusevich",
                    replacement_player_name="Michael Rushton",
                    score_difference=0.0,
                    revision_after=1,
                ),
            ),
            revision=1,
        )
        page = MatchPage()

        page.show_results(
            MatchAnalysisResult(
                player_count=11,
                opponent_name="Rival FC",
                formations=[result],
                analyzed_formations=["2-5-3"],
            ),
            workspace_state=state,
        )

        self.assertEqual(
            board_order_map(page._formation_board_widget.current_board()),
            lineup_order_map(result),
        )


if __name__ == "__main__":
    unittest.main()
