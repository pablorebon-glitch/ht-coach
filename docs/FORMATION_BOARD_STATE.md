# Formation Board State

Alpha 0.6.7 HF-05 documents the state contract for the editable Match
Formation Board.

## Stable tactical slots

The board is slot-authoritative. A slot id represents a stable tactical place in
the formation: formation, line, position, side and index. Players can move between
slots, but the slot's tactical identity does not move with the player.

Starter-to-starter swaps exchange the players assigned to two slots and preserve
each slot's current individual order when that order is still legal for the slot.
If an order is no longer legal for the affected slot, only that slot is normalized
back to `Normal`. The service does not rerun the order optimizer after a manual
starter swap.

Bench replacements still validate the incoming player against the target slot and
may normalize the affected slot if its previous order is not valid for the new
assignment. Unaffected slots are never rewritten as part of a local edit.

## Manual order updates

Manual order changes are resolved by `slot_id` plus the expected workspace
revision, not by player name or player id alone. This prevents a stale inspector
control from updating the wrong player after a swap.

The Qt order selector blocks signals while it is being populated, applies the
state change through `WorkspaceService.set_manual_order_for_slot()`, emits the
normal workspace-modified signal for the controller, and defers the visual rebuild
until the current combo-box signal has returned. That avoids deleting or
reparenting the active sender while PySide6 is still dispatching the signal.

## Persistence

Persisted lineup snapshots keep serializable view-model data only: slot ids,
players, formation, side, position, individual order, order side, tactic and team
attitude. They never store optimizer objects.

## Engine boundary

HF-05 changes application workspace state and Formation Board UI behavior only. It
does not alter rating formulas, probability calculations, PRE/POST parsers,
lineup optimizers, tactic optimizers or order scoring.
