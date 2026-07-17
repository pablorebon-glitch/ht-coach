import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
)
from ht_coach_app.widgets.formation_board.formation_layouts import (
    get_formation_layout,
)
from ht_coach_app.workspace.workspace_service import WorkspaceService
from models.opponent import Opponent
from models.player import Player
from models.position import Position
from models.team_ratings import TeamRatings


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


def roster_for_result(result):
    names = {
        player.player_name
        for player in result.lineup
    }
    players = [
        make_player(name)
        for name in sorted(names)
    ]
    players.extend(
        [
            make_player("A Replacement", scoring=11, passing=7),
            make_player("B Replacement", scoring=10, passing=7),
            make_player("C Replacement", scoring=9, passing=7),
        ]
    )
    return players


class FakeOpponentService:
    def __init__(self):
        self.opponent = Opponent(
            name="Rival FC",
            ratings=TeamRatings(
                left_defense=25,
                central_defense=35,
                right_defense=24,
                midfield=40,
                left_attack=25,
                central_attack=30,
                right_attack=24,
            ),
        )

    def list_opponents(self):
        return [self.opponent]

    def get_opponent(self, name):
        if name == self.opponent.name:
            return self.opponent
        return None


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
        self.assertEqual(
            state.status_label,
            "Modified Workspace - Pending Recalculation",
        )

    def test_replacement_preview_apply_cancel_and_reset(self):
        state = self.service.create([self.board], "3-5-2")
        candidate = self.service.replacement_candidates(
            state,
            self.roster,
        )[0]

        previewed = self.service.preview_replacement(state, candidate)
        self.assertIsNotNone(previewed.replacement_preview)
        self.assertEqual(previewed.status_label, "Replacement Preview")

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

    def test_status_transitions_original_pending_evaluated_pending_and_reset(self):
        state = self.service.create([self.board], "3-5-2")
        self.assertEqual(state.status_label, "Original Recommendation")

        candidate = self.service.replacement_candidates(
            state,
            self.roster,
        )[0]
        state = self.service.preview_replacement(state, candidate)
        state = self.service.apply_replacement(state, self.roster)
        self.assertEqual(
            state.status_label,
            "Modified Workspace - Pending Recalculation",
        )

        evaluated_board = FormationBoardMapper().to_board(
            formation_result(selected_forward="A Replacement")
        )
        state = self.service.with_evaluated_boards(
            state,
            [evaluated_board],
        )
        self.assertEqual(state.status_label, "Evaluated Workspace")
        self.assertEqual(
            state.current_board.selected_player.player_name,
            "A Replacement",
        )

        next_candidate = self.service.replacement_candidates(
            state,
            self.roster,
        )[0]
        state = self.service.preview_replacement(state, next_candidate)
        state = self.service.apply_replacement(state, self.roster)
        self.assertEqual(
            state.status_label,
            "Modified Workspace - Pending Recalculation",
        )

        state = self.service.reset(state)
        self.assertEqual(state.status_label, "Original Recommendation")
        self.assertEqual(state.current_board.selected_player_id, "")

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

    def test_swap_preview_does_not_mutate_until_apply(self):
        state = self.service.create([self.board], "3-5-2")
        slots = [
            slot for slot in state.current_board.slots if slot.player is not None
        ]
        source = slots[0]
        target = slots[1]

        previewed = self.service.preview_swap(
            state,
            source.slot_id,
            target.slot_id,
        )

        self.assertIsNotNone(previewed.swap_preview)
        self.assertEqual(previewed.status_label, "Swap Preview")
        self.assertEqual(
            previewed.current_board.slots[0].player.player_name,
            source.player.player_name,
        )
        self.assertEqual(
            previewed.current_board.slots[1].player.player_name,
            target.player.player_name,
        )

    def test_apply_swap_keeps_slot_tactics_attached_to_slots(self):
        state = self.service.create([self.board], "3-5-2")
        slots = [
            slot for slot in state.current_board.slots if slot.player is not None
        ]
        source = slots[0]
        target = slots[1]

        state = self.service.preview_swap(
            state,
            source.slot_id,
            target.slot_id,
        )
        applied = self.service.apply_preview(state, self.roster)
        updated_source_slot = next(
            slot for slot in applied.current_board.slots
            if slot.slot_id == source.slot_id
        )
        updated_target_slot = next(
            slot for slot in applied.current_board.slots
            if slot.slot_id == target.slot_id
        )

        self.assertEqual(
            updated_source_slot.player.player_name,
            target.player.player_name,
        )
        self.assertEqual(
            updated_source_slot.player.position,
            source.player.position,
        )
        self.assertEqual(
            updated_target_slot.player.player_name,
            source.player.player_name,
        )
        self.assertEqual(
            updated_target_slot.player.position,
            target.player.position,
        )
        self.assertEqual(applied.revision, state.revision + 1)
        self.assertEqual(len(applied.history), 1)
        self.assertEqual(applied.history[0].kind, "swap")

    def test_stale_replacement_preview_is_rejected_safely(self):
        state = self.service.create([self.board], "3-5-2")
        candidate = self.service.replacement_candidates(
            state,
            self.roster,
        )[0]
        previewed = self.service.preview_replacement(state, candidate)
        stale = self.service.reset(previewed)
        stale = stale.__class__(
            **{
                **stale.__dict__,
                "replacement_preview": previewed.replacement_preview,
            }
        )

        applied = self.service.apply_preview(stale, self.roster)

        self.assertIn("out of date", applied.last_error)
        self.assertFalse(applied.dirty)
        self.assertEqual(
            applied.current_board.slots[0].player.player_name,
            state.current_board.slots[0].player.player_name,
        )

    def test_drag_replacement_preview_matches_click_replacement_preview(self):
        state = self.service.create([self.board], "3-5-2")
        selected_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        candidate = self.service.replacement_candidates(
            state,
            self.roster,
        )[0]

        click_state = self.service.preview_replacement(state, candidate)
        drag_candidate = self.service.candidate_for_player(
            state,
            self.roster,
            candidate.player_id,
            selected_slot.slot_id,
        )
        drag_state = self.service.preview_replacement_for_slot(
            state,
            drag_candidate,
            selected_slot.slot_id,
        )

        self.assertEqual(
            click_state.replacement_preview,
            drag_state.replacement_preview,
        )

    def test_invalid_drag_revision_is_rejected_without_crashing(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
        )

        valid, message = self.service.validate_swap(
            state,
            {
                "source_type": "lineup",
                "source_slot_id": target_slot.slot_id,
                "formation_name": "3-5-2",
                "revision": "not-a-number",
            },
            target_slot.slot_id,
        )

        self.assertFalse(valid)
        self.assertIn("lineup changed", message)


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
            lambda state: recalculate_calls.append(state)
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
            "Replacement Preview",
        )

        board_widget.apply_replacement_button.click()
        self.assertEqual(recalculate_calls, [])
        self.assertIn(
            "Pending Recalculation",
            board_widget.workspace_status_label.text(),
        )
        self.assertEqual(
            board_widget.current_board().selected_player.player_name,
            "A Replacement",
        )

        board_widget.recalculate_button.click()
        self.assertEqual(len(recalculate_calls), 1)
        self.assertEqual(
            recalculate_calls[0].current_board.selected_player.player_name,
            "A Replacement",
        )

    def test_match_page_routes_workspace_recalculate_to_workspace_signal(self):
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
        workspace_calls = []
        page.workspace_recalculate_requested.connect(
            lambda state: workspace_calls.append(state)
        )
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
        self.assertEqual(calls, [])
        self.assertEqual(len(workspace_calls), 1)

    def test_board_routes_lineup_drop_to_swap_preview(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )
        slots = [
            slot for slot in board_widget.current_board().slots
            if slot.player is not None
        ]
        payload = {
            "source_type": "lineup",
            "player_id": slots[0].player.player_id,
            "source_slot_id": slots[0].slot_id,
            "formation_name": board_widget.current_board().formation_name,
            "revision": board_widget.workspace_state().revision,
        }

        board_widget._handle_player_dropped(payload, slots[1].slot_id)

        self.assertIsNotNone(board_widget.workspace_state().swap_preview)
        self.assertEqual(
            board_widget.workspace_status_label.text(),
            "Swap Preview",
        )

    def test_board_routes_candidate_drop_to_replacement_preview(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )
        target_slot = next(
            slot for slot in board_widget.current_board().slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        payload = {
            "source_type": "candidate",
            "player_id": "a_replacement",
            "formation_name": board_widget.current_board().formation_name,
            "revision": board_widget.workspace_state().revision,
        }

        board_widget._handle_player_dropped(payload, target_slot.slot_id)

        self.assertIsNotNone(
            board_widget.workspace_state().replacement_preview
        )
        self.assertEqual(
            board_widget.workspace_status_label.text(),
            "Replacement Preview",
        )

    def test_escape_cancels_preview_without_resetting_workspace(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )
        player_id = next(
            slot.player.player_id
            for slot in board_widget.current_board().slots
            if slot.player.player_name == "Rushton"
        )
        board_widget.select_player(player_id)
        board_widget.findChild(QPushButton, "replacementCandidate").click()

        from PySide6.QtCore import QCoreApplication, QEvent, Qt
        from PySide6.QtGui import QKeyEvent

        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        QCoreApplication.sendEvent(board_widget, event)

        self.assertIsNone(board_widget.workspace_state().replacement_preview)
        self.assertFalse(board_widget.workspace_state().dirty)

    def test_recalculated_workspace_result_preserves_applied_replacement(self):
        result = formation_result()
        board = FormationBoardMapper().to_board(result)
        service = WorkspaceService()
        state = service.create([board], "3-5-2")
        forward_id = next(
            slot.player.player_id
            for slot in state.current_board.slots
            if slot.player.player_name == "Rushton"
        )
        state = service.select_player(state, forward_id)
        roster = roster_for_result(result)
        candidate = service.replacement_candidates(state, roster)[0]
        state = service.preview_replacement(state, candidate)
        state = service.apply_replacement(state, roster)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "players.csv"
            path.write_text("placeholder", encoding="utf-8")
            match_service = MatchWorkspaceService(
                FakeOpponentService(),
                importer=lambda _path: roster,
                optimizer=lambda *_args, **_kwargs: self.fail(
                    "lineup optimizer should not run for workspace recalculation"
                ),
            )
            recalculated = match_service.analyze_workspace(
                path,
                "Rival FC",
                state,
            )

        self.assertEqual(
            recalculated.recommended_formation.lineup[
                result.lineup.index(
                    next(player for player in result.lineup if player.player_name == "Rushton")
                )
            ].player_name,
            candidate.player_name,
        )

    def test_recalculated_workspace_preserves_multiple_replacements(self):
        result = formation_result()
        board = FormationBoardMapper().to_board(result)
        service = WorkspaceService()
        state = service.create([board], "3-5-2")
        roster = roster_for_result(result) + [
            make_player("Defender Replacement", defending=12),
        ]

        for current_name in ("Rushton", "Center Central Defender (CD) 3"):
            player_id = next(
                slot.player.player_id
                for slot in state.current_board.slots
                if slot.player.player_name == current_name
            )
            state = service.select_player(state, player_id)
            candidate = service.replacement_candidates(state, roster)[0]
            state = service.preview_replacement(state, candidate)
            state = service.apply_replacement(state, roster)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "players.csv"
            path.write_text("placeholder", encoding="utf-8")
            match_service = MatchWorkspaceService(
                FakeOpponentService(),
                importer=lambda _path: roster,
                optimizer=lambda *_args, **_kwargs: self.fail(
                    "lineup optimizer should not run for workspace recalculation"
                ),
            )
            recalculated = match_service.analyze_workspace(
                path,
                "Rival FC",
                state,
            )

        names = [
            player.player_name
            for player in recalculated.recommended_formation.lineup
        ]
        self.assertIn("A Replacement", names)
        self.assertIn("Defender Replacement", names)
        self.assertNotIn("Rushton", names)

    @staticmethod
    def _board_model():
        return board_with_selected_forward()


if __name__ == "__main__":
    unittest.main()
