from copy import deepcopy
from dataclasses import replace

from engine.analyzers.player_analyzer import PlayerAnalyzer
from engine.calculators.contribution_calculator import ContributionCalculator
from engine.orders.order_modifier import OrderModifier
from engine.optimizers.order_optimizer import OrderOptimizer
from ht_coach_app.core.position_formatting import format_position
from ht_coach_app.core.position_formatting import format_position_abbreviation
from ht_coach_app.core.position_formatting import normalize_position_key
from ht_coach_app.core.side_formatting import format_side
from ht_coach_app.workspace.workspace_models import (
    LineupRecommendationSet,
    ManualLineupState,
    OrderRecommendation,
    PositionRecommendation,
    RecommendationImpact,
    WorkspaceBenchPlayer,
    WorkspaceModification,
    WorkspaceReplacementCandidate,
    WorkspaceReplacementPreview,
    WorkspaceState,
    WorkspaceSwapPreview,
)
from models.order import Order
from models.position import Position
from models.side import Side


MAX_REPLACEMENT_CANDIDATES = 5
MIN_RECOMMENDATION_IMPROVEMENT = 0.01
SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
    "midfield",
    "left_attack",
    "central_attack",
    "right_attack",
)


class WorkspaceService:
    def __init__(self, analyzer=PlayerAnalyzer):
        self._analyzer = analyzer

    def create(
        self,
        boards,
        selected_formation_name="",
        roster_players=(),
        optimize_orders=True,
    ):
        finalized_boards = (
            [
                self.optimize_orders_for_lineup(board, roster_players)[0]
                for board in boards
            ]
            if optimize_orders
            else list(boards)
        )
        original = {
            board.formation_name: deepcopy(board)
            for board in finalized_boards
        }
        workspace = {
            board.formation_name: board
            for board in finalized_boards
        }
        current = selected_formation_name or (
            finalized_boards[0].formation_name if finalized_boards else ""
        )
        if current not in workspace:
            current = finalized_boards[0].formation_name if finalized_boards else ""

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

    def click_player(self, state, roster_players, player_id, interaction_source="CLICK"):
        board = state.current_board
        if board is None:
            return state

        clicked_slot = self._slot_by_player_id(board, player_id)
        if clicked_slot is None:
            return self._error(self.clear_selection(state), "Invalid lineup operation.")

        selected_slot = self._selected_slot(board)
        if selected_slot is None:
            return self.select_player(state, player_id)

        if selected_slot.slot_id == clicked_slot.slot_id:
            return self.clear_selection(state)

        applied = self.swap_slots_immediately(
            state,
            board.formation_name,
            selected_slot.slot_id,
            clicked_slot.slot_id,
            state.revision,
            roster_players=roster_players,
            interaction_source=interaction_source,
        )
        if not applied.last_error:
            applied = self.clear_selection(applied)
        return applied

    def cancel_selection(self, state):
        return self.clear_selection(state)

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
        return self._mark_ready(applied)

    def swap_slots_immediately(
        self,
        state,
        formation_name,
        source_slot_id,
        target_slot_id,
        expected_revision,
        roster_players=(),
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
            roster_players=roster_players,
            interaction_source=interaction_source,
        )
        return self._mark_ready(applied)

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
            if self._is_goalkeeper_slot(source_slot) != self._is_goalkeeper_slot(target_slot):
                return False, "Goalkeepers can only move to goalkeeper slots."
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
        if self._is_goalkeeper_slot(source_slot) != self._is_goalkeeper_slot(target_slot):
            return self._error(state, "Goalkeepers can only move to goalkeeper slots.")

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
            return self.apply_swap(state, roster_players=roster_players)
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
        updated_board, order_changes = self._apply_best_orders_to_slots(
            updated_board,
            roster_players,
            (preview.slot_id,),
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
            order_changes=order_changes,
        )

        return replace(
            state,
            workspace_boards=boards,
            selected_player_id=preview.replacement_player_id,
            replacement_preview=None,
            swap_preview=None,
            history=state.history + (modification,),
            redo_stack=(),
            evaluation_state="ready",
            revision=state.revision + 1,
            last_error="",
            manual_lineup_state=ManualLineupState.MANUALLY_MODIFIED,
            recommendations=LineupRecommendationSet(
                manual_state=ManualLineupState.MANUALLY_MODIFIED,
                stale_revision=state.revision + 1,
            ),
        )

    def apply_swap(self, state, roster_players=(), interaction_source=""):
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
        updated_board, order_changes = self._apply_best_orders_to_slots(
            updated_board,
            roster_players,
            (preview.source_slot_id, preview.target_slot_id),
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
            order_changes=order_changes,
        )

        return replace(
            state,
            workspace_boards=boards,
            selected_player_id=source.player_id,
            replacement_preview=None,
            swap_preview=None,
            history=state.history + (modification,),
            redo_stack=(),
            evaluation_state="ready",
            revision=state.revision + 1,
            last_error="",
            manual_lineup_state=ManualLineupState.MANUALLY_MODIFIED,
            recommendations=LineupRecommendationSet(
                manual_state=ManualLineupState.MANUALLY_MODIFIED,
                stale_revision=state.revision + 1,
            ),
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
            manual_lineup_state=ManualLineupState.OPTIMIZED,
            recommendations=LineupRecommendationSet(
                manual_state=ManualLineupState.OPTIMIZED,
                stale_revision=state.revision + 1,
            ),
        )

    def analyze_recommendations(self, state, roster_players):
        board = state.current_board
        if board is None:
            return state

        current_score, current_totals = self._board_score(board, roster_players)
        order_recommendations, order_score, _order_totals = self._order_recommendations(
            board,
            roster_players,
            current_score,
            current_totals,
        )
        recommendations = LineupRecommendationSet(
            manual_state=(
                ManualLineupState.RECOMMENDATIONS_AVAILABLE
                if order_recommendations
                else state.manual_lineup_state
            ),
            position_recommendations=(),
            order_recommendations=tuple(order_recommendations),
            objective="formation_score",
            current_score=current_score,
            recommended_score=max(order_score, current_score),
            stale_revision=state.revision,
            no_position_recommendation_reason="manual_positions_are_authoritative",
            no_order_recommendation_reason=(
                "" if order_recommendations else "current_order_already_recommended"
            ),
        )
        return replace(
            state,
            manual_lineup_state=recommendations.manual_state,
            recommendations=recommendations,
            evaluation_state="ready",
            last_error="",
        )

    def optimize_orders_for_slots(self, state, roster_players, slot_ids):
        board = state.current_board
        if board is None:
            return state
        updated_board, order_changes = self.optimize_orders_for_lineup(
            board,
            roster_players,
            slot_ids,
        )
        if updated_board == board:
            return replace(state, evaluation_state="ready", last_error="")
        boards = dict(state.workspace_boards)
        boards[updated_board.formation_name] = updated_board
        history = state.history
        if order_changes and history:
            history = history[:-1] + (
                replace(history[-1], order_changes=order_changes),
            )
        return replace(
            state,
            workspace_boards=boards,
            history=history,
            evaluation_state="ready",
            last_error="",
        )

    def optimize_orders_for_lineup(self, board, roster_players, slot_ids=None):
        if not roster_players:
            return board, ()

        target_slot_ids = tuple(
            slot.slot_id
            for slot in board.slots
            if slot.player is not None
        ) if slot_ids is None else tuple(slot_ids)
        return self._apply_best_orders_to_slots(
            board,
            roster_players,
            target_slot_ids,
        )

    def apply_position_recommendations(self, state):
        recommendations = state.recommendations
        if recommendations.stale_revision != state.revision:
            return self._error(state, "Recommendations are out of date.")
        board = state.current_board
        if board is None or not recommendations.position_recommendations:
            return state

        assignments = {
            item.current_slot_id: item.recommended_slot_id
            for item in recommendations.position_recommendations
        }
        source_by_slot = {
            slot.slot_id: slot
            for slot in board.slots
            if slot.player is not None
        }
        player_for_target = {}
        for source_slot_id, target_slot_id in assignments.items():
            source_slot = source_by_slot.get(source_slot_id)
            target_slot = source_by_slot.get(target_slot_id)
            if source_slot is None or target_slot is None:
                return self._error(state, "Recommendations are out of date.")
            player_for_target[target_slot_id] = self._assign_player_to_slot(
                source_slot.player,
                target_slot,
                selected=False,
            )

        updated_slots = []
        for slot in board.slots:
            if slot.slot_id in player_for_target:
                updated_slots.append(replace(slot, player=player_for_target[slot.slot_id]))
            else:
                updated_slots.append(slot)

        return self._apply_recommended_board(
            state,
            replace(board, slots=tuple(updated_slots), selected_player_id=""),
            "position_recommendations",
        )

    def apply_order_recommendations(self, state):
        recommendations = state.recommendations
        if recommendations.stale_revision != state.revision:
            return self._error(state, "Recommendations are out of date.")
        board = state.current_board
        if board is None or not recommendations.order_recommendations:
            return state

        by_player = {
            item.player_id: item
            for item in recommendations.order_recommendations
        }
        updated_slots = []
        for slot in board.slots:
            player = slot.player
            if player is None or player.player_id not in by_player:
                updated_slots.append(slot)
                continue
            recommendation = by_player[player.player_id]
            updated_slots.append(
                replace(
                    slot,
                    player=replace(
                        player,
                        individual_order=recommendation.recommended_order,
                        order_label=recommendation.recommended_order,
                        order_side=recommendation.recommended_order_side,
                        order_side_label=format_side(
                            recommendation.recommended_order_side
                        ),
                        is_modified=True,
                    ),
                )
            )

        return self._apply_recommended_board(
            state,
            replace(board, slots=tuple(updated_slots), selected_player_id=""),
            "order_recommendations",
        )

    def apply_position_recommendation(self, state, player_id):
        recommendations = state.recommendations
        if recommendations.stale_revision != state.revision:
            return self._error(state, "Recommendations are out of date.")
        board = state.current_board
        if board is None:
            return state
        recommendation = next(
            (
                item
                for item in recommendations.position_recommendations
                if item.player_id == player_id
            ),
            None,
        )
        if recommendation is None:
            return self._error(state, "No recommendation available.")

        updated_board = self._swapped_board(
            board,
            recommendation.current_slot_id,
            recommendation.recommended_slot_id,
        )
        if updated_board == board:
            return self._error(state, "No recommendation available.")
        return self._apply_recommended_board(
            state,
            replace(updated_board, selected_player_id=""),
            "position_recommendation",
        )

    def apply_order_recommendation(self, state, player_id):
        recommendations = state.recommendations
        if recommendations.stale_revision != state.revision:
            return self._error(state, "Recommendations are out of date.")
        board = state.current_board
        if board is None:
            return state
        recommendation = next(
            (
                item
                for item in recommendations.order_recommendations
                if item.player_id == player_id
            ),
            None,
        )
        if recommendation is None:
            return self._error(state, "No recommendation available.")
        return self._apply_recommended_board(
            state,
            self._board_with_order(
                board,
                recommendation.player_id,
                self._order(recommendation.recommended_order),
            ),
            "order_recommendation",
        )

    def apply_all_recommendations(self, state, roster_players=None):
        state = self.apply_position_recommendations(state)
        if state.last_error:
            return state
        if state.recommendations.stale_revision != state.revision:
            state = self.analyze_recommendations(state, roster_players or [])
        return self.apply_order_recommendations(state)

    def with_evaluated_boards(self, state, boards):
        selected_player_id = state.selected_player_id
        evaluated_by_name = {
            board.formation_name: board
            for board in boards
        }
        workspace_boards = {}

        board_names = tuple(
            dict.fromkeys(
                tuple(state.workspace_boards.keys())
                + tuple(evaluated_by_name.keys())
            )
        )
        for formation_name in board_names:
            board = evaluated_by_name.get(
                formation_name,
                state.workspace_boards.get(formation_name),
            )
            if board is None:
                continue
            if state.dirty and formation_name in state.workspace_boards:
                board = self._merge_evaluated_board_metadata(
                    state.workspace_boards[formation_name],
                    board,
                )
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
            evaluation_state="ready",
            last_error="",
        )

    def mark_updating(self, state):
        return replace(
            state,
            replacement_preview=None,
            swap_preview=None,
            evaluation_state="analyzing",
            last_error="",
        )

    def mark_failed(self, state, message):
        return replace(
            state,
            replacement_preview=None,
            swap_preview=None,
            evaluation_state="error",
            last_error=message,
        )

    def _position_recommendations(self, board, roster_players, current_score):
        working = board
        recommendations = []
        score = current_score
        totals = self._empty_totals()
        improved = True

        while improved:
            improved = False
            best = None
            slots = [slot for slot in working.slots if slot.player is not None]
            for source in slots:
                if source.position == Position.GOALKEEPER.value:
                    continue
                for target in slots:
                    if source.slot_id >= target.slot_id:
                        continue
                    if target.position == Position.GOALKEEPER.value:
                        continue
                    candidate = self._swapped_board(working, source.slot_id, target.slot_id)
                    candidate_score, candidate_totals = self._board_score(
                        candidate,
                        roster_players,
                    )
                    improvement = candidate_score - score
                    if improvement <= MIN_RECOMMENDATION_IMPROVEMENT:
                        continue
                    if best is None or improvement > best[0]:
                        best = (
                            improvement,
                            source,
                            target,
                            candidate,
                            candidate_score,
                            candidate_totals,
                        )

            if best is not None:
                improvement, source, target, candidate, score, totals = best
                deltas = self._sector_deltas(
                    self._board_score(working, roster_players)[1],
                    totals,
                )
                recommendations.extend(
                    [
                        PositionRecommendation(
                            player_id=source.player.player_id,
                            player_display_name=source.player.player_name,
                            current_slot_id=source.slot_id,
                            recommended_slot_id=target.slot_id,
                            current_position=source.player.position,
                            recommended_position=target.position,
                            current_side=source.side,
                            recommended_side=target.side,
                            impact=RecommendationImpact(
                                affected_sectors=tuple(sector for sector, _ in deltas),
                                sector_deltas=deltas,
                                aggregate_improvement=round(improvement, 4),
                            ),
                        ),
                        PositionRecommendation(
                            player_id=target.player.player_id,
                            player_display_name=target.player.player_name,
                            current_slot_id=target.slot_id,
                            recommended_slot_id=source.slot_id,
                            current_position=target.player.position,
                            recommended_position=source.position,
                            current_side=target.side,
                            recommended_side=source.side,
                            impact=RecommendationImpact(
                                affected_sectors=tuple(sector for sector, _ in deltas),
                                sector_deltas=deltas,
                                aggregate_improvement=round(improvement, 4),
                            ),
                        ),
                    ]
                )
                working = candidate
                improved = True

        if not recommendations:
            score, totals = self._board_score(board, roster_players)
        return working, tuple(recommendations), score, totals

    def _order_recommendations(self, board, roster_players, current_score, current_totals):
        recommendations = []
        working = board
        score = current_score
        totals = current_totals
        for slot in working.slots:
            player_card = slot.player
            if player_card is None:
                continue
            current_order = self._order(player_card.individual_order)
            best_order = current_order
            best_score = score
            best_totals = totals
            for order in self.valid_orders_for_position(player_card.position):
                candidate = self._board_with_order(working, player_card.player_id, order)
                candidate_score, candidate_totals = self._board_score(
                    candidate,
                    roster_players,
                )
                if candidate_score > best_score + MIN_RECOMMENDATION_IMPROVEMENT:
                    best_order = order
                    best_score = candidate_score
                    best_totals = candidate_totals
            if best_order == current_order:
                continue
            deltas = self._sector_deltas(totals, best_totals)
            recommendations.append(
                OrderRecommendation(
                    player_id=player_card.player_id,
                    player_display_name=player_card.player_name,
                    slot_id=slot.slot_id,
                    current_order=current_order.value,
                    recommended_order=best_order.value,
                    position=player_card.position,
                    side=player_card.side,
                    impact=RecommendationImpact(
                        affected_sectors=tuple(sector for sector, _ in deltas),
                        sector_deltas=deltas,
                        aggregate_improvement=round(best_score - score, 4),
                    ),
                )
            )
            working = self._board_with_order(working, player_card.player_id, best_order)
            score = best_score
            totals = best_totals

        return tuple(recommendations), score, totals

    @staticmethod
    def valid_orders_for_position(position):
        return tuple(
            configuration.order
            for configuration in WorkspaceService.valid_order_configurations_for_position(
                position
            )
        )

    @staticmethod
    def valid_order_configurations_for_position(position):
        normalized = WorkspaceService._position(position)
        return OrderOptimizer.ALLOWED_CONFIGURATIONS.get(
            normalized,
            OrderOptimizer.ALLOWED_CONFIGURATIONS[Position.GOALKEEPER],
        )

    def _apply_best_orders_to_slots(self, board, roster_players, slot_ids):
        target_ids = set(slot_ids)
        updated = board
        changes = []
        for slot_id in slot_ids:
            slot = self._slot_by_id(updated, slot_id)
            if slot is None or slot.player is None:
                continue
            best_order, best_side = self._best_order_for_slot(
                updated,
                roster_players,
                slot_id,
            )
            current_order = self._order(slot.player.individual_order)
            current_side = self._optional_side(slot.player.order_side)
            if best_order == current_order and best_side == current_side:
                continue
            updated = self._board_with_order(
                updated,
                slot.player.player_id,
                best_order,
                best_side,
            )
            changes.append(
                (
                    slot.player.player_name,
                    self._format_order_change(current_order, current_side),
                    self._format_order_change(best_order, best_side),
                )
            )
        if not target_ids:
            return board, ()
        return updated, tuple(changes)

    def _best_order_for_slot(self, board, roster_players, slot_id):
        slot = self._slot_by_id(board, slot_id)
        if slot is None or slot.player is None:
            return Order.NORMAL, None
        current_order = self._order(slot.player.individual_order)
        current_side = self._optional_side(slot.player.order_side)
        current_score, _ = self._board_score(board, roster_players)
        best_order = current_order
        best_side = current_side
        best_score = current_score
        current_configuration_seen = False
        configurations = self.valid_order_configurations_for_position(
            slot.player.position
        )
        for configuration in configurations:
            if (
                configuration.order == current_order
                and configuration.order_side == current_side
            ):
                current_configuration_seen = True
            candidate = self._board_with_order(
                board,
                slot.player.player_id,
                configuration.order,
                configuration.order_side,
            )
            candidate_score, _ = self._board_score(candidate, roster_players)
            if candidate_score > best_score + MIN_RECOMMENDATION_IMPROVEMENT:
                best_order = configuration.order
                best_side = configuration.order_side
                best_score = candidate_score
        if current_configuration_seen:
            return best_order, best_side
        normal = next(
            configuration
            for configuration in configurations
            if configuration.order == Order.NORMAL
        )
        if best_score <= current_score + MIN_RECOMMENDATION_IMPROVEMENT:
            return normal.order, normal.order_side
        return best_order, best_side

    def _board_score(self, board, roster_players):
        totals = self._empty_totals()
        for slot in board.slots:
            if slot.player is None:
                continue
            player = self._find_player(roster_players, slot.player.player_name)
            if player is None:
                continue
            contribution = ContributionCalculator.calculate(
                player,
                self._position(slot.player.position).value,
                self._side(slot.player.side),
            )
            contribution = OrderModifier.apply(
                contribution,
                self._position(slot.player.position),
                self._side(slot.player.side),
                self._order(slot.player.individual_order),
                self._optional_side(slot.player.order_side),
            )
            for sector in SECTORS:
                totals[sector] += float(getattr(contribution, sector))
        return round(sum(totals.values()), 4), totals

    def _swapped_board(self, board, source_slot_id, target_slot_id):
        source_slot = self._slot_by_id(board, source_slot_id)
        target_slot = self._slot_by_id(board, target_slot_id)
        if source_slot is None or target_slot is None:
            return board
        source = source_slot.player
        target = target_slot.player
        if source is None or target is None:
            return board
        return replace(
            board,
            slots=tuple(
                replace(slot, player=self._assign_player_to_slot(target, source_slot))
                if slot.slot_id == source_slot_id
                else (
                    replace(slot, player=self._assign_player_to_slot(source, target_slot))
                    if slot.slot_id == target_slot_id
                    else slot
                )
                for slot in board.slots
            ),
        )

    def _board_with_order(self, board, player_id, order, order_side=None):
        order_side_value = getattr(order_side, "value", order_side) or ""
        return replace(
            board,
            slots=tuple(
                replace(
                    slot,
                    player=(
                        replace(
                            slot.player,
                            individual_order=order.value,
                            order_label=order.value,
                            order_side=order_side_value,
                            order_side_label=format_side(order_side_value),
                        )
                        if slot.player is not None
                        and slot.player.player_id == player_id
                        else slot.player
                    ),
                )
                for slot in board.slots
            ),
        )

    def _apply_recommended_board(self, state, board, kind):
        boards = dict(state.workspace_boards)
        boards[board.formation_name] = self.clear_board_selection(board)
        modification = WorkspaceModification(
            formation_name=board.formation_name,
            slot_id="",
            role="",
            original_player_name="",
            replacement_player_name="",
            score_difference=round(
                state.recommendations.recommended_score
                - state.recommendations.current_score,
                4,
            ),
            kind=kind,
            before_lineup_ids=self._lineup_ids(state.current_board),
            after_lineup_ids=self._lineup_ids(board),
            revision_before=state.revision,
            revision_after=state.revision + 1,
        )
        return replace(
            state,
            workspace_boards=boards,
            selected_player_id="",
            replacement_preview=None,
            swap_preview=None,
            history=state.history + (modification,),
            redo_stack=(),
            evaluation_state="pending",
            revision=state.revision + 1,
            last_error="",
            manual_lineup_state=ManualLineupState.RECOMMENDATIONS_APPLIED,
            recommendations=LineupRecommendationSet(
                manual_state=ManualLineupState.RECOMMENDATIONS_APPLIED,
                stale_revision=state.revision + 1,
                current_score=state.recommendations.current_score,
                recommended_score=state.recommendations.recommended_score,
            ),
        )

    @staticmethod
    def _empty_totals():
        return {sector: 0.0 for sector in SECTORS}

    @staticmethod
    def _sector_deltas(before, after):
        deltas = []
        for sector in SECTORS:
            delta = round(after.get(sector, 0.0) - before.get(sector, 0.0), 4)
            if abs(delta) > MIN_RECOMMENDATION_IMPROVEMENT:
                deltas.append((sector, delta))
        return tuple(deltas)

    @staticmethod
    def _format_order_change(order, order_side=None):
        if order_side is None:
            return order.value
        return f"{order.value} {format_side(order_side)}"

    @staticmethod
    def _is_goalkeeper_slot(slot):
        position = getattr(slot, "position", "")
        return normalize_position_key(position) == Position.GOALKEEPER.value

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

    @staticmethod
    def _merge_evaluated_board_metadata(current_board, evaluated_board):
        return replace(
            current_board,
            tactic_name=evaluated_board.tactic_name,
            tactic_level=evaluated_board.tactic_level,
            recommendation_label=evaluated_board.recommendation_label,
            restored=evaluated_board.restored,
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
    def _mark_ready(state):
        return replace(
            state,
            replacement_preview=None,
            swap_preview=None,
            evaluation_state="ready",
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
    def _slot_by_player_id(board, player_id):
        if board is None:
            return None
        for slot in board.slots:
            if slot.player is not None and slot.player.player_id == player_id:
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
    def _optional_side(side):
        value = getattr(side, "value", side)
        if not value:
            return None
        try:
            return Side(str(value))
        except ValueError:
            return None

    @staticmethod
    def _position(position):
        value = normalize_position_key(position)
        try:
            return Position(str(value))
        except ValueError:
            return Position.GOALKEEPER

    @staticmethod
    def _order(order):
        value = getattr(order, "value", order)
        text = str(value or "").strip()
        for candidate in Order:
            if text in (candidate.name, candidate.value):
                return candidate
        return Order.NORMAL

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
        template_player = getattr(slot_template, "player", None) or slot_template
        position = getattr(slot_template, "position", getattr(template_player, "position", ""))
        position_label = getattr(
            slot_template,
            "position_label",
            format_position(position),
        )
        side = getattr(slot_template, "side", getattr(template_player, "side", ""))
        side_label = getattr(
            slot_template,
            "side_label",
            format_side(side),
        )
        return replace(
            player,
            position=position,
            position_label=position_label,
            position_abbreviation=format_position_abbreviation(position),
            side=side,
            side_label=side_label,
            individual_order=getattr(player, "individual_order", "Normal"),
            order_label=getattr(player, "order_label", "Normal"),
            order_side=getattr(player, "order_side", ""),
            order_side_label=getattr(player, "order_side_label", ""),
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
