from copy import deepcopy
from dataclasses import replace

from engine.analyzers.player_analyzer import PlayerAnalyzer
from ht_coach_app.core.position_formatting import format_position
from ht_coach_app.core.position_formatting import format_position_abbreviation
from ht_coach_app.core.position_formatting import normalize_position_key
from ht_coach_app.core.side_formatting import format_side
from ht_coach_app.workspace.workspace_models import (
    WorkspaceBenchPlayer,
    WorkspaceModification,
    WorkspaceReplacementCandidate,
    WorkspaceReplacementPreview,
    WorkspaceState,
    WorkspaceSwapPreview,
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
            swap_preview=None,
            revision=state.revision + (1 if state.has_preview else 0),
            last_error="",
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
            swap_preview=None,
            last_error="",
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
            swap_preview=None,
            last_error="",
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

    def derive_bench(self, state, roster_players, selected_bench_player_id=""):
        board = state.current_board
        if board is None or not roster_players:
            return ()

        lineup_ids = self._lineup_roster_ids(board)
        selected_slot = self._selected_slot(board)
        selected_position = (
            selected_slot.player.position
            if selected_slot is not None and selected_slot.player is not None
            else ""
        )
        selected_side = (
            selected_slot.player.side
            if selected_slot is not None and selected_slot.player is not None
            else ""
        )
        selected_ranking = (
            self._rank_players(roster_players, selected_position, selected_side)
            if selected_position
            else ()
        )
        bench = []

        for player in roster_players:
            player_id = self._player_id(player.name)
            if player_id in lineup_ids:
                continue

            best_position, best_score = self._analyzer.best_position(player)
            best_key = normalize_position_key(best_position)
            compatibility = ""
            score = float(best_score)
            if selected_position:
                selected_score = self._score_for(selected_ranking, player.name)
                score = selected_score
                compatibility = self._compatibility_label(
                    selected_score,
                    self._score_for(
                        selected_ranking,
                        selected_slot.player.player_name,
                    ),
                )

            bench.append(
                WorkspaceBenchPlayer(
                    player_id=player_id,
                    player_name=player.name,
                    best_position=best_key,
                    best_position_label=format_position(best_key),
                    best_position_abbreviation=format_position_abbreviation(
                        best_key
                    ),
                    score=round(score, 2),
                    compatibility_label=compatibility,
                    is_selected=player_id == selected_bench_player_id,
                    is_incoming_preview=(
                        state.replacement_preview is not None
                        and state.replacement_preview.replacement_player_id
                        == player_id
                    ),
                )
            )

        return tuple(
            sorted(
                bench,
                key=lambda item: (
                    self._bench_position_rank(item.best_position),
                    -float(item.score),
                    item.player_name,
                    item.player_id,
                ),
            )
        )

    def preview_replacement(self, state, candidate):
        board = state.current_board
        selected_slot = self._selected_slot(board)
        if selected_slot is None:
            return state

        return self.preview_replacement_for_slot(
            state,
            candidate,
            selected_slot.slot_id,
        )

    def preview_replacement_for_slot(self, state, candidate, target_slot_id):
        board = state.current_board
        selected_slot = self._slot_by_id(board, target_slot_id)
        selected = selected_slot.player if selected_slot is not None else None
        if board is None or selected is None:
            return self._error(state, "Choose an occupied slot first.")

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
            revision=state.revision,
        )
        return replace(
            state,
            replacement_preview=preview,
            swap_preview=None,
            last_error="",
        )

    def cancel_replacement(self, state):
        return replace(
            state,
            replacement_preview=None,
            swap_preview=None,
            last_error="",
        )

    def candidate_for_player(self, state, roster_players, player_id, target_slot_id):
        board = state.current_board
        target_slot = self._slot_by_id(board, target_slot_id)
        target = target_slot.player if target_slot is not None else None
        if board is None or target is None:
            return None

        ranking = self._rank_players(
            roster_players,
            target.position,
            target.side,
        )
        target_score = self._score_for(ranking, target.player_name)
        current_lineup_names = {
            slot.player.player_name
            for slot in board.slots
            if slot.player is not None
        }

        for player_score in ranking:
            player = player_score.player
            candidate_id = self._player_id(player.name)
            if candidate_id != player_id:
                continue
            if player.name in current_lineup_names:
                return None
            difference = round(float(player_score.score) - target_score, 2)
            return WorkspaceReplacementCandidate(
                player_id=candidate_id,
                player_name=player.name,
                score=float(player_score.score),
                score_difference=difference,
                reason=self._candidate_reason(difference),
            )

        return None

    def preview_bench_exchange(self, state, roster_players, target_slot_id, bench_player_id):
        valid, message = self.validate_bench_exchange(
            state,
            roster_players,
            target_slot_id,
            bench_player_id,
        )
        if not valid:
            return self._error(state, message)

        candidate = self.candidate_for_player(
            state,
            roster_players,
            bench_player_id,
            target_slot_id,
        )
        if candidate is None:
            return self._error(
                state,
                "This bench player cannot replace that slot.",
            )

        return self.preview_replacement_for_slot(
            state,
            candidate,
            target_slot_id,
        )

    def replace_slot_immediately(
        self,
        state,
        roster_players,
        formation_name,
        target_slot_id,
        incoming_player_id,
        expected_revision,
        interaction_source="",
    ):
        valid, message = self._validate_immediate_intent(
            state,
            formation_name,
            expected_revision,
        )
        if not valid:
            return self._error(state, message)

        previewed = self.preview_bench_exchange(
            state,
            roster_players,
            target_slot_id,
            incoming_player_id,
        )
        if previewed.replacement_preview is None:
            return previewed

        applied = self.apply_replacement(
            previewed,
            roster_players,
            interaction_source=interaction_source,
        )
        return self._mark_pending(applied)

    def swap_slots_immediately(
        self,
        state,
        formation_name,
        source_slot_id,
        target_slot_id,
        expected_revision,
        interaction_source="",
    ):
        valid, message = self._validate_immediate_intent(
            state,
            formation_name,
            expected_revision,
        )
        if not valid:
            return self._error(state, message)

        previewed = self.preview_swap(
            state,
            source_slot_id,
            target_slot_id,
        )
        if previewed.swap_preview is None:
            return previewed

        applied = self.apply_swap(
            previewed,
            interaction_source=interaction_source,
        )
        return self._mark_pending(applied)

    def validate_bench_exchange(self, state, roster_players, target_slot_id, bench_player_id):
        board = state.current_board
        if board is None:
            return False, "No formation is selected."
        target_slot = self._slot_by_id(board, target_slot_id)
        if target_slot is None or target_slot.player is None:
            return False, "Drop onto an occupied lineup slot."
        bench_ids = {
            item.player_id
            for item in self.derive_bench(state, roster_players)
        }
        if bench_player_id not in bench_ids:
            return False, "This player is not available on the bench."
        return True, ""

    def can_drop(self, state, payload, target_slot_id):
        return self.validate_swap(state, payload, target_slot_id)[0]

    def validate_swap(self, state, payload, target_slot_id):
        board = state.current_board
        if board is None:
            return False, "No formation is selected."
        try:
            payload_revision = int(payload.get("revision", -1))
        except (TypeError, ValueError):
            payload_revision = -1
        if payload_revision != state.revision:
            return False, "The lineup changed. Try the drag again."
        if payload.get("formation_name") != board.formation_name:
            return False, "Switch back to the source formation first."
        target_slot = self._slot_by_id(board, target_slot_id)
        if target_slot is None or target_slot.player is None:
            return False, "Drop onto an occupied lineup slot."
        if payload.get("source_type") == "lineup":
            source_slot_id = payload.get("source_slot_id", "")
            source_slot = self._slot_by_id(board, source_slot_id)
            if source_slot is None or source_slot.player is None:
                return False, "The dragged player is no longer in this lineup."
            if source_slot_id == target_slot_id:
                return False, "Drop onto a different slot to swap players."
            return True, ""
        if payload.get("source_type") in ("candidate", "bench"):
            if not payload.get("player_id"):
                return False, "The replacement candidate is unavailable."
            return True, ""
        return False, "This item cannot be dropped on the lineup."

    def preview_swap(self, state, source_slot_id, target_slot_id):
        board = state.current_board
        source_slot = self._slot_by_id(board, source_slot_id)
        target_slot = self._slot_by_id(board, target_slot_id)
        source = source_slot.player if source_slot is not None else None
        target = target_slot.player if target_slot is not None else None
        if source is None or target is None:
            return self._error(state, "Both lineup slots must be occupied.")
        if source_slot_id == target_slot_id:
            return self._error(state, "Choose a different slot to swap players.")

        return replace(
            state,
            replacement_preview=None,
            swap_preview=WorkspaceSwapPreview(
                formation_name=board.formation_name,
                source_slot_id=source_slot_id,
                target_slot_id=target_slot_id,
                source_player_id=source.player_id,
                source_player_name=source.player_name,
                target_player_id=target.player_id,
                target_player_name=target.player_name,
                source_role=self._role_label(source),
                target_role=self._role_label(target),
                revision=state.revision,
            ),
            last_error="",
        )

    def apply_preview(self, state, roster_players):
        if state.replacement_preview is not None:
            return self.apply_replacement(state, roster_players)
        if state.swap_preview is not None:
            return self.apply_swap(state)
        return state

    def apply_replacement(self, state, roster_players, interaction_source=""):
        preview = state.replacement_preview
        board = state.current_board
        if preview is None or board is None:
            return state
        if preview.revision != state.revision:
            return self._error(
                self.cancel_replacement(state),
                "The preview is out of date. Try the change again.",
            )
        current_slot = self._slot_by_id(board, preview.slot_id)
        if current_slot is None or current_slot.player is None:
            return self._error(
                self.cancel_replacement(state),
                "The target slot changed. Try the change again.",
            )
        if current_slot.player.player_id != preview.current_player_id:
            return self._error(
                self.cancel_replacement(state),
                "The target player changed. Try the change again.",
            )
        if self._lineup_contains_roster_id(
            board,
            preview.replacement_player_id,
        ):
            return self._error(
                self.cancel_replacement(state),
                "The incoming player is already in the lineup.",
            )

        replacement_player = self._find_player(
            roster_players,
            preview.replacement_player_name,
        )
        if replacement_player is None:
            return self._error(
                self.cancel_replacement(state),
                "The incoming player is no longer available in the roster.",
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
        before_ids = self._lineup_ids(board)
        after_ids = self._lineup_ids(updated_board)
        modification = WorkspaceModification(
            formation_name=preview.formation_name,
            slot_id=preview.slot_id,
            role=preview.role,
            original_player_name=preview.current_player_name,
            replacement_player_name=preview.replacement_player_name,
            score_difference=preview.score_difference,
            kind="replacement",
            target_slot_id=preview.slot_id,
            incoming_player_id=preview.replacement_player_id,
            outgoing_player_id=preview.current_player_id,
            before_lineup_ids=before_ids,
            after_lineup_ids=after_ids,
            revision_before=state.revision,
            revision_after=state.revision + 1,
            interaction_source=interaction_source,
            previous_slot_score=preview.current_score,
            current_slot_score=preview.replacement_score,
        )

        return replace(
            state,
            workspace_boards=boards,
            selected_player_id=preview.replacement_player_id,
            replacement_preview=None,
            swap_preview=None,
            history=state.history + (modification,),
            redo_stack=(),
            evaluation_state="pending",
            revision=state.revision + 1,
            last_error="",
        )

    def apply_swap(self, state, interaction_source=""):
        preview = state.swap_preview
        board = state.current_board
        if preview is None or board is None:
            return state
        if preview.revision != state.revision:
            return self._error(
                self.cancel_replacement(state),
                "The preview is out of date. Try the swap again.",
            )

        source_slot = self._slot_by_id(board, preview.source_slot_id)
        target_slot = self._slot_by_id(board, preview.target_slot_id)
        source = source_slot.player if source_slot is not None else None
        target = target_slot.player if target_slot is not None else None
        if source is None or target is None:
            return self._error(state, "The swap cannot be applied safely.")

        source_for_target = self._assign_player_to_slot(source, target, selected=True)
        target_for_source = self._assign_player_to_slot(target, source, selected=False)
        updated_slots = []
        for slot in board.slots:
            if slot.slot_id == preview.source_slot_id:
                updated_slots.append(replace(slot, player=target_for_source))
            elif slot.slot_id == preview.target_slot_id:
                updated_slots.append(replace(slot, player=source_for_target))
            else:
                updated_slots.append(slot)

        updated_board = replace(
            board,
            slots=tuple(updated_slots),
            selected_player_id=source.player_id,
        )
        boards = dict(state.workspace_boards)
        boards[updated_board.formation_name] = updated_board
        before_ids = self._lineup_ids(board)
        after_ids = self._lineup_ids(updated_board)
        modification = WorkspaceModification(
            formation_name=preview.formation_name,
            slot_id=preview.target_slot_id,
            role=preview.target_role,
            original_player_name=preview.target_player_name,
            replacement_player_name=preview.source_player_name,
            score_difference=0.0,
            kind="swap",
            source_slot_id=preview.source_slot_id,
            target_slot_id=preview.target_slot_id,
            incoming_player_id=preview.source_player_id,
            outgoing_player_id=preview.target_player_id,
            before_lineup_ids=before_ids,
            after_lineup_ids=after_ids,
            revision_before=state.revision,
            revision_after=state.revision + 1,
            interaction_source=interaction_source,
        )

        return replace(
            state,
            workspace_boards=boards,
            selected_player_id=source.player_id,
            replacement_preview=None,
            swap_preview=None,
            history=state.history + (modification,),
            redo_stack=(),
            evaluation_state="pending",
            revision=state.revision + 1,
            last_error="",
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
            revision=state.revision + 1,
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
            swap_preview=None,
            evaluation_state="evaluated",
            revision=state.revision + 1,
            last_error="",
        )

    def mark_updating(self, state):
        return replace(
            state,
            replacement_preview=None,
            swap_preview=None,
            evaluation_state="updating",
            last_error="",
        )

    def mark_failed(self, state, message):
        return replace(
            state,
            replacement_preview=None,
            swap_preview=None,
            evaluation_state="failed",
            last_error=message,
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
    def _lineup_ids(board):
        if board is None:
            return ()
        return tuple(
            slot.player.player_id
            for slot in board.slots
            if slot.player is not None
        )

    def _lineup_roster_ids(self, board):
        if board is None:
            return set()
        return {
            self._player_id(slot.player.player_name)
            for slot in board.slots
            if slot.player is not None
        }

    def _lineup_contains_roster_id(self, board, roster_player_id):
        return roster_player_id in self._lineup_roster_ids(board)

    @staticmethod
    def _validate_immediate_intent(state, formation_name, expected_revision):
        board = state.current_board
        if board is None:
            return False, "No formation is selected."
        if formation_name != board.formation_name:
            return False, "Switch back to the source formation first."
        try:
            revision = int(expected_revision)
        except (TypeError, ValueError):
            revision = -1
        if revision != state.revision:
            return False, "The lineup changed. Try the action again."
        return True, ""

    @staticmethod
    def _mark_pending(state):
        return replace(
            state,
            replacement_preview=None,
            swap_preview=None,
            evaluation_state="pending",
            last_error="",
        )

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
    def _slot_by_id(board, slot_id):
        if board is None:
            return None
        for slot in board.slots:
            if slot.slot_id == slot_id:
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
    def _compatibility_label(candidate_score, selected_score):
        difference = float(candidate_score) - float(selected_score)
        if difference >= 0.5:
            return "Strong fit"
        if difference >= -0.5:
            return "Compatible"
        return "Valid but suboptimal"

    @staticmethod
    def _bench_position_rank(position):
        order = {
            "goalkeeper": 0,
            "central_defender": 1,
            "wing_back": 1,
            "inner_midfielder": 2,
            "winger": 3,
            "forward": 4,
        }
        return order.get(normalize_position_key(position), 5)

    @staticmethod
    def _display_name(player_name):
        name = str(player_name or "").strip()
        if len(name) <= 18:
            return name
        return f"{name[:15].rstrip()}..."

    @staticmethod
    def _player_id(name):
        return str(name or "").strip().replace(" ", "_").lower()

    @staticmethod
    def _assign_player_to_slot(player, slot_template, selected=False):
        return replace(
            player,
            position=slot_template.position,
            position_label=slot_template.position_label,
            position_abbreviation=slot_template.position_abbreviation,
            side=slot_template.side,
            side_label=slot_template.side_label,
            individual_order=slot_template.individual_order,
            order_label=slot_template.order_label,
            order_side=slot_template.order_side,
            order_side_label=slot_template.order_side_label,
            is_selected=selected,
            is_modified=True,
            is_replacement_preview=False,
        )

    @staticmethod
    def _error(state, message):
        return replace(
            state,
            last_error=message,
        )
