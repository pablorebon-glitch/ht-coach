import os
import tempfile
import unittest
from dataclasses import replace
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
from ht_coach_app.workspace.workspace_models import (
    LineupRecommendationSet,
    ManualLineupState,
    OrderRecommendation,
    RecommendationImpact,
)
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
            "Lineup manually modified",
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
            "Lineup manually modified",
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
            "Lineup manually modified",
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
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.position != Position.GOALKEEPER.value
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
        source_after_preview = next(
            slot for slot in previewed.current_board.slots
            if slot.slot_id == source.slot_id
        )
        target_after_preview = next(
            slot for slot in previewed.current_board.slots
            if slot.slot_id == target.slot_id
        )
        self.assertEqual(
            source_after_preview.player.player_name,
            source.player.player_name,
        )
        self.assertEqual(
            target_after_preview.player.player_name,
            target.player.player_name,
        )

    def test_apply_swap_keeps_slot_tactics_attached_to_slots(self):
        state = self.service.create([self.board], "3-5-2")
        slots = [
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.position != Position.GOALKEEPER.value
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

    def test_click_to_click_swaps_two_starters_through_canonical_service(self):
        state = self.service.create([self.board], "3-5-2")
        state = self.service.clear_selection(state)
        slots = [
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.position != Position.GOALKEEPER.value
        ]
        first = slots[0]
        second = slots[1]

        state = self.service.click_player(
            state,
            self.roster,
            first.player.player_id,
        )
        self.assertEqual(state.current_board.selected_player_id, first.player.player_id)
        state = self.service.click_player(
            state,
            self.roster,
            second.player.player_id,
        )

        updated_first = next(
            slot for slot in state.current_board.slots
            if slot.slot_id == first.slot_id
        )
        updated_second = next(
            slot for slot in state.current_board.slots
            if slot.slot_id == second.slot_id
        )
        lineup_ids = [
            slot.player.player_id
            for slot in state.current_board.slots
            if slot.player is not None
        ]

        self.assertEqual(updated_first.player.player_name, second.player.player_name)
        self.assertEqual(updated_second.player.player_name, first.player.player_name)
        self.assertEqual(len(lineup_ids), 11)
        self.assertEqual(len(lineup_ids), len(set(lineup_ids)))
        self.assertEqual(state.current_board.selected_player_id, "")
        self.assertEqual(state.history[-1].interaction_source, "CLICK")

    def test_click_and_drag_starter_swaps_produce_equivalent_lineup_state(self):
        state = self.service.create([self.board], "3-5-2")
        state = self.service.clear_selection(state)
        slots = [
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.position != Position.GOALKEEPER.value
        ]
        first = slots[0]
        second = slots[1]

        click = self.service.click_player(
            state,
            self.roster,
            first.player.player_id,
        )
        click = self.service.click_player(
            click,
            self.roster,
            second.player.player_id,
        )
        drag = self.service.swap_slots_immediately(
            state,
            "3-5-2",
            first.slot_id,
            second.slot_id,
            state.revision,
            interaction_source="DRAG",
        )
        drag = self.service.clear_selection(drag)

        self.assertEqual(
            [
                slot.player.player_id
                for slot in click.current_board.slots
                if slot.player is not None
            ],
            [
                slot.player.player_id
                for slot in drag.current_board.slots
                if slot.player is not None
            ],
        )
        self.assertEqual(click.history[-1].kind, drag.history[-1].kind)

    def test_same_player_click_cancels_without_modifying_lineup(self):
        state = self.service.create([self.board], "3-5-2")
        state = self.service.clear_selection(state)
        player_id = next(
            slot.player.player_id
            for slot in state.current_board.slots
            if slot.player is not None
            and slot.position != Position.GOALKEEPER.value
        )

        selected = self.service.click_player(state, self.roster, player_id)
        cancelled = self.service.click_player(selected, self.roster, player_id)

        self.assertEqual(cancelled.current_board.selected_player_id, "")
        self.assertFalse(cancelled.dirty)
        self.assertEqual(cancelled.revision, state.revision)

    def test_position_recommendation_preserves_formation_and_current_starters(self):
        result = formation_result()
        board = FormationBoardMapper().to_board(result)
        state = self.service.create([board], "3-5-2")
        forward_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        defender_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and "Central Defender" in slot.player.player_name
        )
        roster = [
            make_player(player.player_name)
            for player in result.lineup
        ]
        roster = [
            make_player("Rushton", scoring=15, defending=1, playmaking=2)
            if player.name == "Rushton"
            else (
                make_player(player.name, scoring=1, defending=15, playmaking=2)
                if player.name == defender_slot.player.player_name
                else player
            )
            for player in roster
        ]

        state = self.service.swap_slots_immediately(
            state,
            "3-5-2",
            forward_slot.slot_id,
            defender_slot.slot_id,
            state.revision,
            interaction_source="TEST",
        )
        analyzed = self.service.analyze_recommendations(state, roster)

        self.assertTrue(analyzed.recommendations.position_recommendations)
        self.assertEqual(
            {
                slot.slot_id
                for slot in analyzed.current_board.slots
            },
            {
                slot.slot_id
                for slot in board.slots
            },
        )
        self.assertEqual(
            {
                slot.player.player_name
                for slot in analyzed.current_board.slots
                if slot.player is not None
            },
            {
                player.player_name
                for player in result.lineup
            },
        )
        self.assertFalse(
            any(
                "Recommended" in recommendation.explanation_code
                for recommendation in analyzed.recommendations.position_recommendations
            )
        )

    def test_apply_position_recommendation_updates_lineup_without_optimizer_rerun(self):
        result = formation_result()
        board = FormationBoardMapper().to_board(result)
        state = self.service.create([board], "3-5-2")
        forward_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        defender_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and "Central Defender" in slot.player.player_name
        )
        roster = [
            make_player(player.player_name)
            for player in result.lineup
        ]
        roster = [
            make_player("Rushton", scoring=15, defending=1, playmaking=2)
            if player.name == "Rushton"
            else (
                make_player(player.name, scoring=1, defending=15, playmaking=2)
                if player.name == defender_slot.player.player_name
                else player
            )
            for player in roster
        ]
        state = self.service.swap_slots_immediately(
            state,
            "3-5-2",
            forward_slot.slot_id,
            defender_slot.slot_id,
            state.revision,
            interaction_source="TEST",
        )
        state = self.service.analyze_recommendations(state, roster)

        applied = self.service.apply_position_recommendations(state)

        restored_forward = next(
            slot for slot in applied.current_board.slots
            if slot.slot_id == forward_slot.slot_id
        )
        self.assertIn(
            restored_forward.player.player_name,
            {
                recommendation.player_display_name
                for recommendation in state.recommendations.position_recommendations
            },
        )
        self.assertEqual(applied.history[-1].kind, "position_recommendations")

    def test_apply_individual_position_recommendation_updates_only_requested_swap(self):
        result = formation_result()
        board = FormationBoardMapper().to_board(result)
        state = self.service.create([board], "3-5-2")
        forward_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        defender_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and "Central Defender" in slot.player.player_name
        )
        roster = [
            make_player(player.player_name)
            for player in result.lineup
        ]
        roster = [
            make_player("Rushton", scoring=15, defending=1, playmaking=2)
            if player.name == "Rushton"
            else (
                make_player(player.name, scoring=1, defending=15, playmaking=2)
                if player.name == defender_slot.player.player_name
                else player
            )
            for player in roster
        ]
        state = self.service.swap_slots_immediately(
            state,
            "3-5-2",
            forward_slot.slot_id,
            defender_slot.slot_id,
            state.revision,
            interaction_source="TEST",
        )
        state = self.service.analyze_recommendations(state, roster)
        recommendation = state.recommendations.position_recommendations[0]

        applied = self.service.apply_position_recommendation(
            state,
            recommendation.player_id,
        )

        target_slot = next(
            slot for slot in applied.current_board.slots
            if slot.slot_id == recommendation.recommended_slot_id
        )
        self.assertEqual(target_slot.player.player_id, recommendation.player_id)
        self.assertEqual(applied.history[-1].kind, "position_recommendation")
        self.assertEqual(
            applied.manual_lineup_state,
            ManualLineupState.RECOMMENDATIONS_APPLIED,
        )

    def test_apply_individual_order_recommendation_updates_only_requested_player(self):
        state = self.service.create([self.board], "3-5-2")
        slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.position == Position.WINGER.value
        )
        recommendation = OrderRecommendation(
            player_id=slot.player.player_id,
            player_display_name=slot.player.player_name,
            slot_id=slot.slot_id,
            current_order="Normal",
            recommended_order="Towards Middle",
            position=slot.player.position,
            side=slot.player.side,
            impact=RecommendationImpact(
                affected_sectors=("midfield",),
                sector_deltas=(("midfield", 0.2),),
                aggregate_improvement=0.2,
            ),
        )
        state = replace(
            state,
            manual_lineup_state=ManualLineupState.RECOMMENDATIONS_AVAILABLE,
            recommendations=LineupRecommendationSet(
                manual_state=ManualLineupState.RECOMMENDATIONS_AVAILABLE,
                order_recommendations=(recommendation,),
                current_score=10.0,
                recommended_score=10.2,
                stale_revision=state.revision,
            ),
        )

        applied = self.service.apply_order_recommendation(
            state,
            recommendation.player_id,
        )

        updated_slot = next(
            slot for slot in applied.current_board.slots
            if slot.slot_id == recommendation.slot_id
        )
        untouched_orders = [
            slot.player.individual_order
            for slot in applied.current_board.slots
            if slot.player is not None
            and slot.slot_id != recommendation.slot_id
        ]
        self.assertEqual(updated_slot.player.individual_order, "Towards Middle")
        self.assertTrue(all(order == "Normal" for order in untouched_orders))
        self.assertEqual(applied.history[-1].kind, "order_recommendation")

    def test_valid_orders_are_enumerated_by_supported_domain_rules_only(self):
        self.assertEqual(
            [order.value for order in self.service.valid_orders_for_position("GOALKEEPER")],
            ["Normal"],
        )
        self.assertIn(
            "Defensive",
            [order.value for order in self.service.valid_orders_for_position("WINGER")],
        )
        self.assertNotIn(
            "Extra Forward",
            [order.value for order in self.service.valid_orders_for_position("FORWARD")],
        )

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

    def test_bench_derives_from_roster_minus_current_lineup(self):
        state = self.service.create([self.board], "3-5-2")
        bench = self.service.derive_bench(state, self.roster)
        bench_names = [player.player_name for player in bench]

        self.assertIn("A Replacement", bench_names)
        self.assertNotIn("Rushton", bench_names)
        self.assertEqual(len(bench_names), len(set(bench_names)))

    def test_bench_ordering_is_deterministic(self):
        state = self.service.create([self.board], "3-5-2")

        first = self.service.derive_bench(state, self.roster)
        second = self.service.derive_bench(state, list(reversed(self.roster)))

        self.assertEqual(first, second)

    def test_bench_exchange_apply_updates_lineup_and_derived_bench(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )

        state = self.service.preview_bench_exchange(
            state,
            self.roster,
            target_slot.slot_id,
            "a_replacement",
        )
        self.assertIsNotNone(state.replacement_preview)
        self.assertEqual(
            state.replacement_preview.replacement_player_name,
            "A Replacement",
        )
        applied = self.service.apply_preview(state, self.roster)
        lineup_names = [
            slot.player.player_name
            for slot in applied.current_board.slots
            if slot.player is not None
        ]
        bench_names = [
            player.player_name
            for player in self.service.derive_bench(applied, self.roster)
        ]

        self.assertIn("A Replacement", lineup_names)
        self.assertIn("Rushton", bench_names)
        self.assertNotIn("A Replacement", bench_names)
        self.assertEqual(len(lineup_names), 11)
        self.assertEqual(len(lineup_names), len(set(lineup_names)))
        self.assertEqual(
            state.original_boards["3-5-2"].selected_player.player_name,
            "Rushton",
        )

    def test_both_bench_exchange_directions_create_equivalent_preview(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )

        bench_to_lineup = self.service.preview_bench_exchange(
            state,
            self.roster,
            target_slot.slot_id,
            "a_replacement",
        )
        starter_to_bench = self.service.preview_bench_exchange(
            state,
            self.roster,
            target_slot.slot_id,
            "a_replacement",
        )

        self.assertEqual(
            bench_to_lineup.replacement_preview,
            starter_to_bench.replacement_preview,
        )

    def test_reset_restores_original_lineup_and_bench(self):
        state = self.service.create([self.board], "3-5-2")
        original_bench_names = {
            player.player_name
            for player in self.service.derive_bench(state, self.roster)
        }
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        state = self.service.preview_bench_exchange(
            state,
            self.roster,
            target_slot.slot_id,
            "a_replacement",
        )
        state = self.service.apply_preview(state, self.roster)

        reset = self.service.reset(state)

        self.assertEqual(
            {
                player.player_name
                for player in self.service.derive_bench(reset, self.roster)
            },
            original_bench_names,
        )
        self.assertEqual(reset.current_board.selected_player_id, "")

    def test_structured_replacement_history_includes_lineup_snapshots(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        state = self.service.preview_bench_exchange(
            state,
            self.roster,
            target_slot.slot_id,
            "a_replacement",
        )
        applied = self.service.apply_preview(state, self.roster)
        modification = applied.history[-1]

        self.assertEqual(modification.kind, "replacement")
        self.assertEqual(modification.target_slot_id, target_slot.slot_id)
        self.assertEqual(modification.incoming_player_id, "a_replacement")
        self.assertEqual(
            modification.outgoing_player_id,
            target_slot.player.player_id,
        )
        self.assertEqual(len(modification.before_lineup_ids), 11)
        self.assertEqual(len(modification.after_lineup_ids), 11)
        self.assertEqual(
            modification.revision_after,
            modification.revision_before + 1,
        )

    def test_missing_roster_player_rejects_bench_preview_apply(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        state = self.service.preview_bench_exchange(
            state,
            self.roster,
            target_slot.slot_id,
            "a_replacement",
        )

        applied = self.service.apply_preview(
            state,
            [player for player in self.roster if player.name != "A Replacement"],
        )

        self.assertIn("no longer available", applied.last_error)
        self.assertFalse(applied.dirty)

    def test_changed_target_occupant_rejects_stale_apply(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        previewed = self.service.preview_bench_exchange(
            state,
            self.roster,
            target_slot.slot_id,
            "a_replacement",
        )
        changed = self.service.preview_bench_exchange(
            state,
            self.roster,
            target_slot.slot_id,
            "b_replacement",
        )
        changed = self.service.apply_preview(changed, self.roster)
        changed = changed.__class__(
            **{
                **changed.__dict__,
                "replacement_preview": previewed.replacement_preview,
                "revision": previewed.revision,
            }
        )

        applied = self.service.apply_preview(changed, self.roster)

        self.assertIn("target player changed", applied.last_error)

    def test_immediate_replacement_commits_without_preview_and_tracks_source(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )

        applied = self.service.replace_slot_immediately(
            state,
            self.roster,
            "3-5-2",
            target_slot.slot_id,
            "a_replacement",
            state.revision,
            interaction_source="CLICK",
        )

        self.assertIsNone(applied.replacement_preview)
        self.assertEqual(applied.revision, state.revision + 1)
        self.assertEqual(applied.history[-1].interaction_source, "CLICK")
        self.assertEqual(applied.history[-1].replacement_player_name, "A Replacement")

    def test_click_and_drag_immediate_replacements_are_equivalent_except_source(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )

        click = self.service.replace_slot_immediately(
            state,
            self.roster,
            "3-5-2",
            target_slot.slot_id,
            "a_replacement",
            state.revision,
            interaction_source="CLICK",
        )
        drag = self.service.replace_slot_immediately(
            state,
            self.roster,
            "3-5-2",
            target_slot.slot_id,
            "a_replacement",
            state.revision,
            interaction_source="DRAG",
        )

        click_names = [
            slot.player.player_name
            for slot in click.current_board.slots
            if slot.player is not None
        ]
        drag_names = [
            slot.player.player_name
            for slot in drag.current_board.slots
            if slot.player is not None
        ]

        self.assertEqual(click_names, drag_names)
        self.assertEqual(
            {
                player.player_name
                for player in self.service.derive_bench(click, self.roster)
            },
            {
                player.player_name
                for player in self.service.derive_bench(drag, self.roster)
            },
        )
        self.assertEqual(
            click.history[-1].target_slot_id,
            drag.history[-1].target_slot_id,
        )
        self.assertNotEqual(
            click.history[-1].interaction_source,
            drag.history[-1].interaction_source,
        )

    def test_stale_immediate_replacement_is_rejected(self):
        state = self.service.create([self.board], "3-5-2")
        target_slot = next(
            slot for slot in state.current_board.slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )

        rejected = self.service.replace_slot_immediately(
            state,
            self.roster,
            "3-5-2",
            target_slot.slot_id,
            "a_replacement",
            state.revision + 1,
            interaction_source="CLICK",
        )

        self.assertIn("lineup changed", rejected.last_error)
        self.assertFalse(rejected.dirty)


try:
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton

    from ht_coach_app.views.match_page import MatchPage
    from ht_coach_app.widgets.formation_board.bench_panel import (
        BenchPanel,
        BenchPlayerCard,
    )
    from ht_coach_app.widgets.formation_board.formation_board import (
        FormationBoard,
    )
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QApplication = None
    FormationBoard = None
    MatchPage = None
    BenchPanel = None
    BenchPlayerCard = None
    QLabel = None
    QPushButton = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class InteractiveWorkspaceQtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_board_ui_replacement_commits_and_requests_recalculation_immediately(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )
        modification_calls = []
        board_widget.workspace_modified.connect(
            lambda state: modification_calls.append(state)
        )

        player_id = next(
            slot.player.player_id
            for slot in board_widget.current_board().slots
            if slot.player.player_name == "Rushton"
        )
        board_widget.select_player(player_id)

        board_widget.preview_bench_player_for_selected_slot("a_replacement")
        self.assertEqual(len(modification_calls), 1)
        self.assertEqual(
            board_widget.workspace_status_label.text(),
            "Updating analysis...",
        )
        self.assertEqual(
            next(
                slot.player.player_name
                for slot in board_widget.current_board().slots
                if slot.player is not None
                and slot.slot_id
                == modification_calls[0].history[-1].target_slot_id
            ),
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
        board.preview_bench_player_for_selected_slot("a_replacement")

        self.assertEqual(calls, [])
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
            and slot.position != Position.GOALKEEPER.value
        ]
        payload = {
            "source_type": "lineup",
            "player_id": slots[0].player.player_id,
            "source_slot_id": slots[0].slot_id,
            "formation_name": board_widget.current_board().formation_name,
            "revision": board_widget.workspace_state().revision,
        }

        board_widget._handle_player_dropped(payload, slots[1].slot_id)

        self.assertIsNone(board_widget.workspace_state().swap_preview)
        self.assertTrue(board_widget.workspace_state().dirty)
        self.assertEqual(
            board_widget.workspace_status_label.text(),
            "Updating analysis...",
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

        self.assertIsNone(
            board_widget.workspace_state().replacement_preview
        )
        self.assertTrue(board_widget.workspace_state().dirty)
        self.assertEqual(
            board_widget.workspace_status_label.text(),
            "Updating analysis...",
        )

    def test_bench_panel_appears_beside_board_with_internal_scroll(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )

        bench = board_widget.findChild(BenchPanel)

        self.assertIsNotNone(bench)
        self.assertTrue(bench.scroll.widgetResizable())
        self.assertGreaterEqual(bench.minimumWidth(), 160)
        self.assertGreater(
            board_widget.pitch.minimumWidth(),
            bench.minimumWidth(),
        )

    def test_bench_cards_are_clickable_focusable_and_keyboard_previewable(self):
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
        card = next(
            item for item in board_widget.findChildren(BenchPlayerCard)
            if item.player.player_name == "A Replacement"
        )

        card.click()
        self.assertEqual(board_widget._selected_bench_player_id, "")
        self.assertTrue(board_widget.workspace_state().dirty)
        self.assertNotEqual(card.focusPolicy(), 0)

        from PySide6.QtCore import QCoreApplication, QEvent, Qt
        from PySide6.QtGui import QKeyEvent

        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
        QCoreApplication.sendEvent(card, event)

        self.assertIsNone(board_widget.workspace_state().replacement_preview)

    def test_click_bench_then_starter_replaces_immediately(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )
        card = next(
            item for item in board_widget.findChildren(BenchPlayerCard)
            if item.player.player_name == "A Replacement"
        )
        starter_id = next(
            slot.player.player_id
            for slot in board_widget.current_board().slots
            if slot.player.player_name == "Rushton"
        )

        card.click()
        self.assertEqual(board_widget._selected_bench_player_id, "a_replacement")
        board_widget.select_player(starter_id)

        self.assertTrue(board_widget.workspace_state().dirty)
        self.assertEqual(board_widget._selected_bench_player_id, "")
        self.assertIn(
            "A Replacement",
            [
                slot.player.player_name
                for slot in board_widget.current_board().slots
                if slot.player is not None
            ],
        )

    def test_clicking_selected_starter_again_deselects_it(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )
        starter_id = next(
            slot.player.player_id
            for slot in board_widget.current_board().slots
            if slot.player.player_name == "Rushton"
        )

        board_widget.select_player(starter_id)
        self.assertEqual(board_widget.current_board().selected_player_id, starter_id)
        board_widget.select_player(starter_id)

        self.assertEqual(board_widget.current_board().selected_player_id, "")

    def test_board_routes_starter_drop_on_bench_card_to_exchange_preview(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )
        source_slot = next(
            slot for slot in board_widget.current_board().slots
            if slot.player is not None
            and slot.player.player_name == "Rushton"
        )
        payload = {
            "source_type": "lineup",
            "player_id": source_slot.player.player_id,
            "source_slot_id": source_slot.slot_id,
            "formation_name": board_widget.current_board().formation_name,
            "revision": board_widget.workspace_state().revision,
        }

        board_widget._handle_starter_dropped_on_bench(
            payload,
            "a_replacement",
        )

        self.assertIsNone(
            board_widget.workspace_state().replacement_preview
        )
        self.assertTrue(board_widget.workspace_state().dirty)
        self.assertEqual(
            board_widget.workspace_state().history[-1].target_slot_id,
            source_slot.slot_id,
        )

    def test_bench_background_has_no_drop_operation(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )

        self.assertFalse(board_widget.bench_panel.acceptDrops())
        self.assertIsNone(board_widget.workspace_state().replacement_preview)

    def test_player_intelligence_replacement_controls_are_removed(self):
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

        self.assertIsNone(
            board_widget.inspector.findChild(QPushButton, "replacementCandidate")
        )

    def test_confirmation_and_manual_recalculate_buttons_are_removed(self):
        board_widget = FormationBoard()
        board_widget.set_boards(
            [self._board_model()],
            roster_players=[
                make_player("Rushton", scoring=8, passing=6),
                make_player("A Replacement", scoring=11, passing=7),
            ],
        )

        texts = [
            button.text()
            for button in board_widget.findChildren(QPushButton)
        ]

        self.assertNotIn("Apply Replacement", texts)
        self.assertNotIn("Cancel Replacement", texts)
        self.assertNotIn("Recalculate Analysis", texts)
        self.assertIn("Reset Workspace", texts)
        self.assertFalse(board_widget.reset_workspace_button.isEnabled())

    def test_player_intelligence_uses_workspace_impact_for_inserted_player(self):
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
        board_widget.preview_bench_player_for_selected_slot("a_replacement")
        inserted_id = next(
            slot.player.player_id
            for slot in board_widget.current_board().slots
            if slot.player is not None
            and slot.player.player_name == "A Replacement"
        )
        board_widget.select_player(inserted_id)

        labels = [
            label.text()
            for label in board_widget.inspector.findChildren(QLabel)
        ]

        self.assertIn("Workspace Impact", labels)
        self.assertIn("Position fit comparison", labels)
        self.assertIn("Difference", labels)
        self.assertTrue(
            any("in this slot" in label for label in labels)
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
        board_widget.preview_bench_player_for_selected_slot("a_replacement")

        from PySide6.QtCore import QCoreApplication, QEvent, Qt
        from PySide6.QtGui import QKeyEvent

        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        QCoreApplication.sendEvent(board_widget, event)

        self.assertIsNone(board_widget.workspace_state().replacement_preview)
        self.assertTrue(board_widget.workspace_state().dirty)

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
