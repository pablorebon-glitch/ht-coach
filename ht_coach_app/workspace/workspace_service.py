from copy import deepcopy
from dataclasses import replace

from engine.analyzers.player_analyzer import PlayerAnalyzer
from ht_coach_app.core.position_formatting import format_position
from ht_coach_app.core.side_formatting import format_side
from ht_coach_app.workspace.workspace_models import (
    WorkspaceModification,
    WorkspaceReplacementCandidate,
    WorkspaceReplacementPreview,
    WorkspaceState,
)
from models.side import Side


MAX_REPLACEMENT_CANDIDATES = 5


class WorkspaceService:
    def __init__(self, analyzer=PlayerAnalyzer):
        self._analyzer = analyzer

    def create(self, boards, selected_formation_name=""):
        original = {
            board.formation_name: deepcopy(board)
            for board in boards
        }
        workspace = {
            board.formation_name: board
            for board in boards
        }
        current = selected_formation_name or (
            boards[0].formation_name if boards else ""
        )
        if current not in workspace:
            current = boards[0].formation_name if boards else ""

        return WorkspaceState(
            original_boards=original,
            workspace_boards=workspace,
            current_formation_name=current,
        )

    def set_formation(self, state, formation_name):
        board = state.workspace_boards.get(formation_name)
        boards = dict(state.workspace_boards)

        if board is not None and board.selected_player_id:
            boards[formation_name] = self.clear_board_selection(board)

        return replace(
            state,
            workspace_boards=boards,
            current_formation_name=formation_name,
            selected_player_id="",
            replacement_preview=None,
        )

    def select_player(self, state, player_id):
        board = state.current_board
        if board is None:
            return state

        updated = self.select_board_player(board, player_id)
        boards = dict(state.workspace_boards)
        boards[updated.formation_name] = updated
        return replace(
            state,
            workspace_boards=boards,
            selected_player_id=player_id,
            replacement_preview=None,
        )

    def clear_selection(self, state):
        board = state.current_board
        if board is None:
            return state

        updated = self.clear_board_selection(board)
        boards = dict(state.workspace_boards)
        boards[updated.formation_name] = updated
        return replace(
            state,
            workspace_boards=boards,
            selected_player_id="",
            replacement_preview=None,
        )

    def replacement_candidates(self, state, roster_players):
        board = state.current_board
        selected = board.selected_player if board is not None else None
        if selected is None or not roster_players:
            return ()

        ranking = self._rank_players(
            roster_players,
            selected.position,
            selected.side,
        )
        selected_score = self._score_for(
            ranking,
            selected.player_name,
        )
        current_lineup_names = {
            slot.player.player_name
            for slot in board.slots
            if slot.player is not None
        }
        candidates = []

        for player_score in ranking:
            player = player_score.player
            if player.name == selected.player_name:
                continue
            if player.name in current_lineup_names:
                continue

            difference = round(float(player_score.score) - selected_score, 2)
            candidates.append(
                WorkspaceReplacementCandidate(
                    player_id=self._player_id(player.name),
                    player_name=player.name,
                    score=float(player_score.score),
                    score_difference=difference,
                    reason=self._candidate_reason(difference),
                )
            )
            if len(candidates) >= MAX_REPLACEMENT_CANDIDATES:
                break

        return tuple(candidates)

    def preview_replacement(self, state, candidate):
        board = state.current_board
        selected_slot = self._selected_slot(board)
        selected = selected_slot.player if selected_slot is not None else None
        if selected is None:
            return state

        preview = WorkspaceReplacementPreview(
            formation_name=board.formation_name,
            slot_id=selected_slot.slot_id,
            role=self._role_label(selected),
            current_player_id=selected.player_id,
            current_player_name=selected.player_name,
            replacement_player_id=candidate.player_id,
            replacement_player_name=candidate.player_name,
            current_score=round(candidate.score - candidate.score_difference, 2),
            replacement_score=round(candidate.score, 2),
            score_difference=candidate.score_difference,
        )
        return replace(
            state,
            replacement_preview=preview,
        )

    def cancel_replacement(self, state):
        return replace(
            state,
            replacement_preview=None,
        )

    def apply_replacement(self, state, roster_players):
        preview = state.replacement_preview
        board = state.current_board
        if preview is None or board is None:
            return state

        replacement_player = self._find_player(
            roster_players,
            preview.replacement_player_name,
        )
        updated_slots = []

        for slot in board.slots:
            if slot.slot_id != preview.slot_id or slot.player is None:
                updated_slots.append(slot)
                continue

            player = replace(
                slot.player,
                player_id=preview.replacement_player_id,
                player_name=preview.replacement_player_name,
                display_name=self._display_name(
                    preview.replacement_player_name
                ),
                position_score=preview.replacement_score,
                specialty=getattr(replacement_player, "speciality", ""),
                is_selected=True,
                is_modified=True,
                is_replacement_preview=False,
            )
            updated_slots.append(
                replace(slot, player=player)
            )

        updated_board = replace(
            board,
            slots=tuple(updated_slots),
            selected_player_id=preview.replacement_player_id,
        )
        boards = dict(state.workspace_boards)
        boards[updated_board.formation_name] = updated_board
        modification = WorkspaceModification(
            formation_name=preview.formation_name,
            slot_id=preview.slot_id,
            role=preview.role,
            original_player_name=preview.current_player_name,
            replacement_player_name=preview.replacement_player_name,
            score_difference=preview.score_difference,
        )

        return replace(
            state,
            workspace_boards=boards,
            selected_player_id=preview.replacement_player_id,
            replacement_preview=None,
            history=state.history + (modification,),
            redo_stack=(),
            evaluation_state="pending",
        )

    def reset(self, state):
        boards = {
            name: self.clear_board_selection(deepcopy(board))
            for name, board in state.original_boards.items()
        }
        return WorkspaceState(
            original_boards=state.original_boards,
            workspace_boards=boards,
            current_formation_name=state.current_formation_name,
        )

    def with_evaluated_boards(self, state, boards):
        selected_player_id = state.selected_player_id
        workspace_boards = {}

        for board in boards:
            updated = self._restore_workspace_markers(
                board,
                state,
            )
            if updated.formation_name == state.current_formation_name:
                updated = self._restore_selection(
                    updated,
                    selected_player_id,
                    self._selected_player_name(state),
                )
            workspace_boards[updated.formation_name] = updated

        return replace(
            state,
            workspace_boards=workspace_boards,
            replacement_preview=None,
            evaluation_state="evaluated",
        )

    def select_board_player(self, board, player_id):
        return replace(
            board,
            selected_player_id=player_id,
            slots=tuple(
                replace(
                    slot,
                    player=(
                        replace(
                            slot.player,
                            is_selected=slot.player.player_id == player_id,
                            is_replacement_preview=False,
                        )
                        if slot.player is not None
                        else None
                    ),
                )
                for slot in board.slots
            ),
        )

    def clear_board_selection(self, board):
        return replace(
            board,
            selected_player_id="",
            slots=tuple(
                replace(
                    slot,
                    player=(
                        replace(
                            slot.player,
                            is_selected=False,
                            is_replacement_preview=False,
                        )
                        if slot.player is not None
                        else None
                    ),
                )
                for slot in board.slots
            ),
        )

    def _restore_workspace_markers(self, board, state):
        modified_slots = {
            modification.slot_id
            for modification in state.history
            if modification.formation_name == board.formation_name
        }

        if not modified_slots:
            return board

        return replace(
            board,
            slots=tuple(
                replace(
                    slot,
                    player=(
                        replace(slot.player, is_modified=True)
                        if slot.player is not None
                        and slot.slot_id in modified_slots
                        else slot.player
                    ),
                )
                for slot in board.slots
            ),
        )

    def _restore_selection(self, board, selected_player_id, selected_player_name):
        if not selected_player_id and not selected_player_name:
            return self.clear_board_selection(board)

        for slot in board.slots:
            if slot.player is None:
                continue
            if (
                slot.player.player_id == selected_player_id
                or slot.player.player_name == selected_player_name
            ):
                return self.select_board_player(
                    board,
                    slot.player.player_id,
                )

        return self.clear_board_selection(board)

    @staticmethod
    def _selected_player_name(state):
        board = state.current_board
        if board is not None and board.selected_player is not None:
            return board.selected_player.player_name
        if state.history:
            return state.history[-1].replacement_player_name
        return ""

    def _rank_players(self, roster_players, position, side):
        ranking = self._analyzer.rank_players(
            roster_players,
            position,
            self._side(side),
        )
        return tuple(
            sorted(
                ranking,
                key=lambda player_score: (
                    -float(player_score.score),
                    player_score.player.name,
                ),
            )
        )

    @staticmethod
    def _score_for(ranking, player_name):
        for player_score in ranking:
            if player_score.player.name == player_name:
                return float(player_score.score)
        return 0.0

    @staticmethod
    def _selected_slot(board):
        if board is None:
            return None
        for slot in board.slots:
            if (
                slot.player is not None
                and slot.player.player_id == board.selected_player_id
            ):
                return slot
        return None

    @staticmethod
    def _find_player(players, player_name):
        for player in players or []:
            if player.name == player_name:
                return player
        return None

    @staticmethod
    def _role_label(player):
        side = format_side(player.side)
        position = format_position(player.position)
        if side and side != "Center":
            return f"{side} {position}"
        return position

    @staticmethod
    def _side(side):
        value = getattr(side, "value", side)
        try:
            return Side(str(value))
        except ValueError:
            return Side.CENTER

    @staticmethod
    def _candidate_reason(difference):
        if abs(difference) < 0.25:
            return "Very close replacement for this role."
        if difference > 0:
            return "Higher role score than the current player."
        return "Lower role score than the current player."

    @staticmethod
    def _display_name(player_name):
        name = str(player_name or "").strip()
        if len(name) <= 18:
            return name
        return f"{name[:15].rstrip()}..."

    @staticmethod
    def _player_id(name):
        return str(name or "").strip().replace(" ", "_").lower()
