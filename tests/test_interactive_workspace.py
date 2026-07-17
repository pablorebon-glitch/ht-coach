import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
)
from ht_coach_app.widgets.formation_board.formation_layouts import (
    get_formation_layout,
)
from ht_coach_app.workspace.workspace_service import WorkspaceService
from models.player import Player
from models.position import Position


def make_player(
    name,
    goalkeeper=1,
    defending=5,
    playmaking=5,
    winger=5,
    passing=5,
    scoring=5,
):
    return Player(
        name=name,
        age=25,
        days=0,
        speciality="",
        form=7,
        stamina=7,
        goalkeeper=goalkeeper,
        defending=defending,
        playmaking=playmaking,
        winger=winger,
        passing=passing,
        scoring=scoring,
        set_pieces=4,
        experience=5,
        leadership=4,
        tsi=1000,
        salary=1000,
    )


def formation_result(name="3-5-2", selected_forward="Rushton"):
    lineup = []
    used_forward = False

    for index, slot in enumerate(get_formation_layout(name)):
        player_name = f"{slot.side_label} {slot.position_label} {index + 1}"
        if slot.position == Position.FORWARD.value and not used_forward:
            player_name = selected_forward
            used_forward = True

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
        tactic_level=7.0,
        win_probability=0.55,
        draw_probability=0.25,
        loss_probability=0.20,
        possession=0.60,
        expected_goals=2.0,
        opponent_expected_goals=1.0,
        lineup=lineup,
        is_recommended=True,
    )


def board_with_selected_forward():
    board = FormationBoardMapper().to_board(
        formation_result()
    )
    player_id = next(
        slot.player.player_id
        for slot in board.slots
        if slot.player is not None
        and slot.player.player_name == "Rushton"
    )
    return FormationBoardMapper().select_player(
        board,
        player_id,
    )


class WorkspaceServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = WorkspaceService()
        self.board = board_with_selected_forward()
        self.roster = [
            make_player("Rushton", scoring=8, passing=6),
            make_player("A Replacement", scoring=11, passing=7),
            make_player("B Replacement", scoring=10, passing=7),
            make_player("C Replacement", scoring=9, passing=7),
            make_player("D Replacement", scoring=8, passing=8),
            make_player("E Replacement", scoring=7, passing=8),
            make_player("F Replacement", scoring=6, passing=8),
        ]

    def test_workspace_creation_keeps_original_recommendation_immutable(self):
        state = self.service.create([self.board], "3-5-2")
        candidates = self.service.replacement_candidates(
            state,
            self.roster,
        )
        state = self.service.preview_replacement(state, candidates[0])
        state = self.service.apply_replacement(state, self.roster)

        original = state.original_boards["3-5-2"].selected_player
        current = state.current_board.selected_player

        self.assertEqual(original.player_name, "Rushton")
        self.assertEqual(current.player_name, "A Replacement")
        self.assertTrue(state.dirty)
        self.assertIn("Ready to Recalculate", state.status_label)

    def test_replacement_preview_apply_cancel_and_reset(self):
        state = self.service.create([self.board], "3-5-2")
        candidate = self.service.replacement_candidates(
            state,
            self.roster,
        )[0]

        previewed = self.service.preview_replacement(state, candidate)
        self.assertIsNotNone(previewed.replacement_preview)
        self.assertEqual(previewed.status_label, "Unsaved Changes")

        canceled = self.service.cancel_replacement(previewed)
        self.assertIsNone(canceled.replacement_preview)
        self.assertFalse(canceled.dirty)

        previewed = self.service.preview_replacement(state, candidate)
        applied = self.service.apply_replacement(previewed, self.roster)
        self.assertTrue(applied.dirty)
        self.assertEqual(
            applied.current_board.selected_player.player_name,
            "A Replacement",
        )

        reset = self.service.reset(applied)
        self.assertFalse(reset.dirty)
        self.assertIsNone(reset.replacement_preview)
        self.assertEqual(reset.current_board.selected_player_id, "")
        self.assertEqual(
            reset.current_board.slots[0].player.is_modified,
            False,
        )

    def test_replacement_ranking_is_compatible_limited_and_deterministic(self):
        state = self.service.create([self.board], "3-5-2")
        first = self.service.replacement_candidates(state, self.roster)
        second = self.service.replacement_candidates(state, self.roster)

        self.assertEqual(len(first), 5)
        self.assertEqual(first, second)
        self.assertNotIn(
            "Rushton",
            [candidate.player_name for candidate in first],
        )
        self.assertEqual(first[0].player_name, "A Replacement")

    def test_selection_persists_after_apply(self):
        state = self.service.create([self.board], "3-5-2")
        candidate = self.service.replacement_candidates(
            state,
            self.roster,
        )[0]
        state = self.service.preview_replacement(state, candidate)
        state = self.service.apply_replacement(state, self.roster)

        self.assertEqual(
            state.selected_player_id,
            state.current_board.selected_player_id,
        )
        self.assertEqual(
            state.current_board.selected_player.player_name,
            "A Replacement",
        )


try:
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton

    from ht_coach_app.views.match_page import MatchPage
    from ht_coach_app.widgets.formation_board.formation_board import (
        FormationBoard,
    )
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QApplication = None
    FormationBoard = None
    MatchPage = None
    QLabel = None
    QPushButton = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class InteractiveWorkspaceQtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_board_ui_state_transitions_do_not_recalculate_until_requested(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )
        recalculate_calls = []
        board_widget.recalculate_requested.connect(
            lambda: recalculate_calls.append("called")
        )

        player_id = next(
            slot.player.player_id
            for slot in board_widget.current_board().slots
            if slot.player.player_name == "Rushton"
        )
        board_widget.select_player(player_id)
        candidate = board_widget.findChild(QPushButton, "replacementCandidate")
        self.assertIsNotNone(candidate)

        candidate.click()
        self.assertEqual(recalculate_calls, [])
        self.assertEqual(
            board_widget.workspace_status_label.text(),
            "Unsaved Changes",
        )

        board_widget.apply_replacement_button.click()
        self.assertEqual(recalculate_calls, [])
        self.assertIn(
            "Ready to Recalculate",
            board_widget.workspace_status_label.text(),
        )
        self.assertEqual(
            board_widget.current_board().selected_player.player_name,
            "A Replacement",
        )

        board_widget.recalculate_button.click()
        self.assertEqual(recalculate_calls, ["called"])

    def test_match_page_routes_workspace_recalculate_to_existing_analysis_signal(self):
        page = MatchPage()
        result = MatchAnalysisResult(
            player_count=11,
            opponent_name="Rival FC",
            formations=[formation_result()],
            analyzed_formations=["3-5-2"],
            players_csv_filename="players.csv",
            completed_at="2026-07-17 12:00:00",
        )
        page.set_roster_players(
            [
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ]
        )
        calls = []
        page.analyze_requested.connect(lambda: calls.append("analyze"))
        page.show_results(result)
        board = page.findChild(FormationBoard)

        player_id = next(
            slot.player.player_id
            for slot in board.current_board().slots
            if slot.player.player_name == "Rushton"
        )
        board.select_player(player_id)
        board.findChild(QPushButton, "replacementCandidate").click()
        board.apply_replacement_button.click()

        self.assertEqual(calls, [])
        board.recalculate_button.click()
        self.assertEqual(calls, ["analyze"])

    @staticmethod
    def _board_model():
        return board_with_selected_forward()


if __name__ == "__main__":
    unittest.main()
