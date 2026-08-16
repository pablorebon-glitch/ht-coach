import unittest

from ht_coach_app.workspace.workspace_service import WorkspaceService
from models.position import Position

from test_interactive_workspace import board_with_selected_forward, make_player


def _slot_for_position(board, position, side=None):
    for slot in board.slots:
        if slot.player is None or slot.player.position != position:
            continue
        if side is not None and slot.player.side != side:
            continue
        return slot
    raise AssertionError(f"no slot found for {position}/{side}")


class ManualReplacementOrderRegressionTests(unittest.TestCase):
    """Alpha 0.6.6, Part 1: replacing a player manually must preserve
    the tactical slot, side, and (initially) the previous order --
    never silently reset unrelated player orders, and always leave
    the new player's order editable afterward."""

    def setUp(self):
        self.service = WorkspaceService()
        self.board = board_with_selected_forward()
        self.roster = [
            make_player("CD Replacement", defending=15, playmaking=2, winger=2, passing=3, scoring=1),
            make_player("Winger Replacement", defending=2, playmaking=4, winger=15, passing=5, scoring=6),
            make_player("Forward Replacement", defending=1, playmaking=2, winger=3, passing=3, scoring=15),
        ]

    def test_replace_central_defender_preserves_slot_and_side(self):
        state = self.service.create([self.board], "3-5-2")
        cd_slot = _slot_for_position(state.current_board, Position.CENTRAL_DEFENDER.value)
        original_side = cd_slot.player.side

        updated = self.service.replace_slot_immediately(
            state, self.roster, "3-5-2", cd_slot.slot_id,
            "cd_replacement", state.revision, interaction_source="TEST",
        )

        new_slot = next(s for s in updated.current_board.slots if s.slot_id == cd_slot.slot_id)
        self.assertEqual(new_slot.player.player_name, "CD Replacement")
        self.assertEqual(new_slot.player.position, Position.CENTRAL_DEFENDER.value)
        self.assertEqual(new_slot.player.side, original_side)
        self.assertFalse(updated.last_error)

    def test_replace_winger_preserves_slot_and_side(self):
        state = self.service.create([self.board], "3-5-2")
        winger_slot = _slot_for_position(state.current_board, Position.WINGER.value)
        original_side = winger_slot.player.side

        updated = self.service.replace_slot_immediately(
            state, self.roster, "3-5-2", winger_slot.slot_id,
            "winger_replacement", state.revision, interaction_source="TEST",
        )

        new_slot = next(s for s in updated.current_board.slots if s.slot_id == winger_slot.slot_id)
        self.assertEqual(new_slot.player.player_name, "Winger Replacement")
        self.assertEqual(new_slot.player.side, original_side)

    def test_replace_forward_then_manually_set_towards_wing(self):
        state = self.service.create([self.board], "3-5-2")
        forward_slot = _slot_for_position(state.current_board, Position.FORWARD.value)

        replaced = self.service.replace_slot_immediately(
            state, self.roster, "3-5-2", forward_slot.slot_id,
            "forward_replacement", state.revision, interaction_source="TEST",
        )
        self.assertFalse(replaced.last_error)
        new_slot = next(s for s in replaced.current_board.slots if s.slot_id == forward_slot.slot_id)
        self.assertEqual(new_slot.player.player_name, "Forward Replacement")

        valid_orders = [
            order.value for order in self.service.valid_orders_for_position(Position.FORWARD.value)
        ]
        self.assertIn("Towards Wing", valid_orders)

        with_order = self.service.set_manual_order(
            replaced, new_slot.player.player_id, "Towards Wing", "LEFT"
        )
        self.assertFalse(with_order.last_error)
        final_slot = next(
            s for s in with_order.current_board.slots if s.slot_id == forward_slot.slot_id
        )
        self.assertEqual(final_slot.player.individual_order, "Towards Wing")
        self.assertEqual(final_slot.player.player_name, "Forward Replacement")

    def test_replacement_never_resets_unrelated_player_orders(self):
        state = self.service.create([self.board], "3-5-2")
        winger_slot = _slot_for_position(state.current_board, Position.WINGER.value)
        other_orders_before = {
            slot.slot_id: slot.player.individual_order
            for slot in state.current_board.slots
            if slot.player is not None and slot.slot_id != winger_slot.slot_id
        }

        updated = self.service.replace_slot_immediately(
            state, self.roster, "3-5-2", winger_slot.slot_id,
            "winger_replacement", state.revision, interaction_source="TEST",
        )

        other_orders_after = {
            slot.slot_id: slot.player.individual_order
            for slot in updated.current_board.slots
            if slot.player is not None and slot.slot_id != winger_slot.slot_id
        }
        self.assertEqual(other_orders_before, other_orders_after)

    def test_change_order_after_replacement_is_possible(self):
        state = self.service.create([self.board], "3-5-2")
        cd_slot = _slot_for_position(state.current_board, Position.CENTRAL_DEFENDER.value)

        replaced = self.service.replace_slot_immediately(
            state, self.roster, "3-5-2", cd_slot.slot_id,
            "cd_replacement", state.revision, interaction_source="TEST",
        )
        new_slot = next(s for s in replaced.current_board.slots if s.slot_id == cd_slot.slot_id)

        updated = self.service.set_manual_order(replaced, new_slot.player.player_id, "Offensive")
        self.assertFalse(updated.last_error)
        final_slot = next(s for s in updated.current_board.slots if s.slot_id == cd_slot.slot_id)
        self.assertEqual(final_slot.player.individual_order, "Offensive")

    def test_detailed_xi_and_pitch_share_the_same_board_after_replacement(self):
        state = self.service.create([self.board], "3-5-2")
        winger_slot = _slot_for_position(state.current_board, Position.WINGER.value)

        updated = self.service.replace_slot_immediately(
            state, self.roster, "3-5-2", winger_slot.slot_id,
            "winger_replacement", state.revision, interaction_source="TEST",
        )

        board_from_workspace = updated.workspace_boards[updated.current_board.formation_name]
        self.assertEqual(board_from_workspace, updated.current_board)

    def test_manual_order_rejects_invalid_order_for_position(self):
        state = self.service.create([self.board], "3-5-2")
        goalkeeper_slot = _slot_for_position(state.current_board, Position.GOALKEEPER.value)

        updated = self.service.set_manual_order(
            state, goalkeeper_slot.player.player_id, "Offensive"
        )
        self.assertTrue(updated.last_error)

    def test_manual_order_does_not_affect_other_slots(self):
        state = self.service.create([self.board], "3-5-2")
        cd_slot = _slot_for_position(state.current_board, Position.CENTRAL_DEFENDER.value)
        other_orders_before = {
            slot.slot_id: slot.player.individual_order
            for slot in state.current_board.slots
            if slot.player is not None and slot.slot_id != cd_slot.slot_id
        }

        updated = self.service.set_manual_order(state, cd_slot.player.player_id, "Defensive")

        other_orders_after = {
            slot.slot_id: slot.player.individual_order
            for slot in updated.current_board.slots
            if slot.player is not None and slot.slot_id != cd_slot.slot_id
        }
        self.assertEqual(other_orders_before, other_orders_after)


if __name__ == "__main__":
    unittest.main()
