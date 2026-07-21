# Interactive Workspace

Alpha 0.4.5 turns the HT Coach Workspace into a one-click tactical lab: lineup edits
commit immediately, fixed-lineup analysis updates automatically, and Reset Workspace is
the only global edit action.

Alpha 0.5.6.2.1 changes Assisted Lineup around manual intent. The initial optimized
lineup remains HT Coach's global recommendation, but every later valid manual slot
assignment is authoritative. HT Coach does not recommend moving the player back; it
automatically chooses the best supported individual order for the player in the slot the
user selected.

Alpha 0.5.6.2.2 completes the initial recommendation transaction. When roster data is
available, Workspace creation now optimizes supported individual orders for every
starter before saving the immutable original snapshot. Initial load, reload and Restore
Optimized Lineup therefore display the same complete recommendation without requiring a
manual swap to reveal non-Normal orders.

Alpha 0.5.6.2.3 applies the same manual-intent rule inside Match refresh. After a
manual swap or replacement, the current player-slot assignment is authoritative. The
refresh path evaluates the assigned lineup, merges evaluated metadata back into the
board and preserves viewport state; it does not rebuild the pitch from the original
recommendation unless the user explicitly restores it.

## Concept

The Match page now separates two lineups:

- Recommended Lineup: the immutable optimizer result.
- Workspace Lineup: the editable copy shown on the Formation Board.
- Bench: a derived view of loaded roster players not present in the displayed Workspace
  Lineup.

The original recommendation is never modified. Manual changes update Workspace state
immediately and schedule automatic fixed-lineup recalculation.

The original recommendation snapshot is captured only after formation selection,
starting eleven selection, slot assignment and automatic order selection are finalized.
Restore copies that snapshot back into the editable Workspace and does not rerun lineup
or order optimization.

## Architecture

```text
FormationBoard
  -> WorkspaceService
  -> WorkspaceState
  -> FormationBoardViewModel copies
  -> existing PlayerAnalyzer ranking
```

`ht_coach_app/workspace/` is UI-independent. It owns the editing model, dirty state,
immediate replacement/swap operations and future undo/redo history shape. Widgets render
this state and emit user intent; they do not mutate lineup slots directly.

`WorkspaceService` is the single canonical editing boundary for click-to-click and
drag-and-drop operations. Qt handlers translate UI gestures into service calls only.
The same `optimize_orders_for_lineup` operation is used for all initial starter slots
and for the affected slots after manual replacements or swaps.

## Workspace Model

Workspace state contains:

- original boards;
- editable workspace boards;
- current formation;
- selected player;
- transient selection;
- modification history;
- redo stack reserved for future use.
- evaluation state: original, updating, evaluated, or failed;
- manual lineup state: optimized, manually modified, recommendations available or
  recommendations applied;
- structured assisted recommendations;
- revision number used to reject stale clicks, drops and analysis results safely.

The dirty flag is derived from history. Reset creates a fresh editable copy from the
original recommendation and clears selection, preview and pending modifications.

## Editing Lifecycle

1. Select a player on the Formation Board.
2. Player Intelligence updates for the selected player.
3. Bench shows loaded roster players not currently assigned to the displayed Workspace
   Lineup.
4. Click a Bench player, drag a Bench player onto an occupied slot, or drag a starter
   onto a Bench player.
5. The replacement commits immediately.
6. HT Coach recalculates the best valid individual order for affected slots.
7. Dependent fixed-lineup analysis can refresh without leaving the board permanently
   busy.

During Match refresh, evaluated boards are reconciled into the existing Workspace by
formation name. If the Workspace is dirty, player cards remain in their current slots
and only evaluated metadata such as tactic labels and levels is merged. The lineup
revision is not incremented by a completed analysis result; revisions represent user
lineup intent and protect the pitch from stale asynchronous results.

Initial and reload lifecycle:

1. Receive optimized formation and lineup from the existing engine/service flow.
2. Map players to Formation Board slots.
3. Evaluate every supported order configuration for each starter through
   `OrderOptimizer.ALLOWED_CONFIGURATIONS`.
4. Select deterministic best orders using the Workspace contribution-total objective.
5. Save the finalized board as both immutable original snapshot and editable Workspace
   copy.
6. Render the Formation Board in Original Recommendation state.

Root cause of the Alpha 0.5.6.2.2 bug: Workspace creation previously deep-copied the
original board before invoking automatic order optimization. The optimizer result and
mapped board could therefore start with valid Normal defaults, while automatic order
selection only ran after manual-edit events.

No probability, xG, tactic, Decision Lab or comparison value changes until fixed-lineup
recalculation completes. Stale results are discarded if the Workspace revision has moved
on, and the local analysis state must always leave analyzing through ready or error.

## Click-To-Click

Click-to-click follows the same operation rules as drag-and-drop:

- starter then starter: swap the two players' slots;
- starter then Bench player: Bench player enters the selected starter slot;
- Bench player then starter: Bench player enters the clicked starter slot;
- same player twice: cancel selection;
- empty pitch area or Escape: cancel selection.

Goalkeepers can only move to goalkeeper slots. Other unusual player choices, such as a
forward in midfield, are accepted when the destination lineup slot is valid. Invalid
operations preserve the lineup and expose concise feedback through Workspace state.

## Bench

The Bench is not stored as a separate editing model. It is recalculated from:

```text
loaded roster players - current Workspace Lineup players
```

Bench ordering is deterministic: broad position group, descending relevant score, player
name, then stable player ID. Reset, immediate edits, formation switch and recalculation
all refresh Bench from the current Workspace state.

Bench replacements reuse existing `PlayerAnalyzer.rank_players` for the target slot
position and side. The outgoing starter and players already in the workspace lineup are
excluded.

## Drag and Drop

Alpha 0.4.5 supports three lineup editing drag paths:

- starting player to starting player: commits a slot swap;
- Bench player to starting slot: commits a Bench exchange;
- starting player to Bench player: commits the same Bench exchange in reverse.

Bench player to Bench player is a no-op. Starting player to empty Bench background is
rejected; a lineup slot is never emptied.

Valid drops mutate the Workspace immediately, optimize affected individual orders and
schedule at most one dependent refresh.
Escape clears only transient selection. If the workspace revision changed after the drag
began, the drop is rejected with a safe message and the user can retry the gesture.

Slots remain the tactical source of truth. When two players are swapped, each player
moves into the destination slot's position, side and normalized pitch coordinate. The
player's order is then recalculated for the assigned slot. For Bench exchanges, the
Bench player enters the target slot, receives an automatic order, and the displaced
starter returns to the derived Bench immediately.

Click and drag use the same `WorkspaceService` operations, so they produce the same
lineup contents, slot assignments, dirty state and dependent refresh behavior.

## Manual Intent and Automatic Orders

After a manual edit, the Workspace accepts the current eleven inside the current
formation as the user's intended lineup.

Manual intent rules:

- the user controls formation, player selection and slot assignment;
- HT Coach controls only the best supported individual order for each assigned slot;
- the system does not display persistent position recommendations that contradict the
  manual slot assignment;
- the original optimized lineup remains available through Restore Optimized Lineup.

Automatic order selection:

- enumerates `OrderOptimizer.ALLOWED_CONFIGURATIONS` for the assigned position;
- evaluates each candidate using the existing workspace internal contribution score;
- preserves the current valid order on ties;
- falls back to Normal when the current order is invalid and no candidate improves the
  score;
- applies the selected order immediately to affected slots only.

For a starter-to-starter swap, both affected slots are recalculated. For a Bench
replacement, only the incoming starter's assigned slot is recalculated. This bounded
transaction prevents an edit -> recommendation -> apply -> edit loop.

## Keyboard Replacement

Drag is not the only editing route. Select a lineup slot, focus or click a Bench card,
then press Enter, Space, or click to commit that replacement. The reverse sequence also
works: select a Bench player, then click a starter.

## Workspace Status

The board shows a compact status indicator:

- Original Recommendation: no workspace edits.
- Lineup manually adjusted: the current Workspace differs from the optimizer snapshot
  because the user made an intentional edit.
- Updating analysis...: fixed-lineup analysis is running.
- Analysis updated: local analysis is ready.
- Could not update analysis: the Workspace lineup is kept, but the latest recalculation
  failed.

## Restore

Restore Optimized Lineup restores:

- original player assignments;
- orders and sides from the recommendation;
- selected player;
- transient selection;
- dirty state.
- recommendation state.

Restore applies immediately and does not rerun lineup optimization.

## Automatic Recalculation

Every valid Workspace edit sends the current Workspace Lineup to the Match worker as a
fixed lineup after a short debounce. The application layer rebuilds an engine `Lineup`
from the editable board,
calculates ratings with the existing `TeamRater`, evaluates tactics with the existing
`TacticOptimizer`, maps the result to the same serializable Match view models, and then
refreshes Decision Lab, Player Intelligence, comparison, Detailed XI and Formation Board.

Workspace recalculation deliberately bypasses lineup optimization. It does not invent
metrics and does not change rating, probability, xG, tactic, order or Decision Lab
formulas.

Immediate refresh after edits is limited to presentation that truly consumes the edited
Workspace lineup: pitch, Bench, selected player detail, sector totals after fixed-lineup
recalculation, Player Intelligence context and assisted recommendations. Match-context
modules such as Decision Lab, Match Intelligence and Tactical Advisor update after the
fixed-lineup recalculation returns. Squad Evolution and Transfer Planner remain based on
their own Squad analyses and are not claimed to describe the manual Workspace lineup.

The debounce coalesces rapid edits. A returning result is applied only when its captured
Workspace revision still matches the latest requested revision.

After recalculation, the Workspace Lineup keeps its committed player assignments and the
original recommendation remains available as the Reset Workspace baseline.

## Change Analysis

Alpha 0.4.6 adds a Change Analysis panel after Workspace recalculation. The panel
compares only calculated values from:

```text
previous evaluated Workspace -> current evaluated Workspace
```

It uses the last Workspace modification to show the incoming player, outgoing player and
slot, then displays the slot fit score difference with explicit `in this slot` wording.
Team impact compares win, draw and loss values before and after recalculation. Sector
Changes lists only rating sectors whose calculated values changed.

The summary is deterministic. It uses simple thresholds over calculated probability and
sector differences to classify the latest change as an excellent trade-off, balanced
improvement, risky change or net negative. It does not call an LLM and does not change
Decision Lab rules, xG, probability or rating calculations.

## Match Layout

Alpha 0.4.3.1 keeps Analysis Setup as a persistent collapsible section. It is expanded
before the first analysis, collapses after success, and can be shown or hidden without
rerunning analysis, clearing results or changing workspace state.

The compact match summary now shows only match context such as `Opponent: Rival FC` and
`Formations: 2`. CSV filename, player count, completion timestamp, copy actions and the
old Edit Analysis button are removed from the visible summary.

The Match page uses an outer vertical scroll area so the Formation Board can keep a
useful minimum height. The pitch itself does not scroll internally. Alpha 0.4.5 reduces
the pitch footprint and preserves the main page scroll position across selection,
Workspace edits and automatic result refreshes.

Alpha 0.5.7 adds reusable collapsible sections to Match results. Decision Lab, Match
Intelligence, Opponent Rating Calibration and Match Analysis each keep an independent
expanded or collapsed state. Defaults are chosen for a first launch: Match Analysis and
Match Intelligence expanded, Decision Lab and Opponent Rating Calibration collapsed.

The collapsible wrapper hides only the section body. It keeps the header and summary
visible, keeps the underlying widgets alive while collapsed, and does not trigger a new
analysis. Result refreshes update collapsed section contents without forcing the section
open. The state is persisted in `match_workspace.json` as `match_section_states` so it
survives tab changes, language changes, workspace refreshes and application restart
where the local settings file is available.

The shared component lives in `ht_coach_app/ui/design_system/collapsible_section.py`.
Headers are clickable across their full width and support Enter and Space. Header text,
summary text and expand/collapse tooltips pass through the localization layer.

## Future Work

The workspace model reserves history and redo state so later milestones can add:

- Undo;
- Redo;
- what-if comparison against the original recommendation.

Alpha 0.4.6 deliberately does not include a long history timeline, Undo/Redo or
animated interactions.

Constraint-Based Lineup Optimizer is explicitly deferred. Future support may include
mandatory players, rest lists, training priorities, locked slots, locked orders and
minimum win-confidence constraints. Alpha 0.5.6.2 only assists edits to the current
lineup.
