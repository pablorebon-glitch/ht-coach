# Interactive Workspace

Alpha 0.4.5 turns the HT Coach Workspace into a one-click tactical lab: lineup edits
commit immediately, fixed-lineup analysis updates automatically, and Reset Workspace is
the only global edit action.

Alpha 0.5.6.2 adds Assisted Lineup behavior on top of that model. Manual lineup edits
remain explicit user actions, while HT Coach can now recommend slot and individual-order
adjustments for the already selected eleven.

## Concept

The Match page now separates two lineups:

- Recommended Lineup: the immutable optimizer result.
- Workspace Lineup: the editable copy shown on the Formation Board.
- Bench: a derived view of loaded roster players not present in the displayed Workspace
  Lineup.

The original recommendation is never modified. Manual changes update Workspace state
immediately and schedule automatic fixed-lineup recalculation.

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
6. Fixed-lineup analysis is scheduled automatically.

No probability, xG, tactic, Decision Lab or comparison value changes until automatic
fixed-lineup recalculation completes. Stale results are discarded if the Workspace
revision has moved on.

## Click-To-Click

Click-to-click follows the same operation rules as drag-and-drop:

- starter then starter: swap the two players' slots;
- starter then Bench player: Bench player enters the selected starter slot;
- Bench player then starter: Bench player enters the clicked starter slot;
- same player twice: cancel selection;
- empty pitch area or Escape: cancel selection.

Goalkeepers can only move to goalkeeper slots. Invalid operations preserve the lineup
and expose concise feedback through Workspace state.

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

Valid drops mutate the Workspace immediately and schedule automatic recalculation.
Escape clears only transient selection. If the workspace revision changed after the drag
began, the drop is rejected with a safe message and the user can retry the gesture.

Slots remain the tactical source of truth. When two players are swapped, the player moves
but the destination slot keeps its position, side, order and normalized pitch coordinate.
For Bench exchanges, the Bench player enters the target slot and the displaced starter
returns to the derived Bench immediately.

Click and drag use the same `WorkspaceService` operations, so they produce the same
lineup contents, slot assignments, dirty state and dependent refresh behavior.

## Assisted Recommendations

After a manual edit, the Workspace can analyze the current eleven inside the current
formation.

Position recommendations:

- reorder only current starters;
- preserve formation structure and goalkeeper constraints;
- prevent duplicate player assignment;
- compare internal contribution totals through existing contribution semantics;
- never add or remove players.

Order recommendations:

- enumerate only orders supported by `OrderModifier`;
- keep Normal when it is already best;
- report affected sectors and internal contribution deltas;
- never imply Hattrick decimal ratings.

Recommendations are structured data, not translated prose. The UI localizes labels at
render time. Applying recommendations is explicit and remains reversible through Reset
Workspace.

## Keyboard Replacement

Drag is not the only editing route. Select a lineup slot, focus or click a Bench card,
then press Enter, Space, or click to commit that replacement. The reverse sequence also
works: select a Bench player, then click a starter.

## Workspace Status

The board shows a compact status indicator:

- Original Recommendation: no workspace edits.
- Lineup manually modified: the current Workspace differs from the optimizer snapshot.
- Recommendations available: assisted recommendations exist for the current revision.
- Recommendations applied: the user explicitly applied assisted recommendations.
- Updating analysis...: a committed edit is waiting for or running fixed-lineup analysis.
- Evaluated Workspace: current metrics were recalculated for the Workspace Lineup.
- Analysis failed: the Workspace lineup is kept, but the latest recalculation failed.

## Reset

Reset Workspace restores:

- original player assignments;
- orders and sides from the recommendation;
- selected player;
- transient selection;
- dirty state.
- recommendation state.

Reset schedules automatic fixed-lineup recalculation when restoring a modified Workspace.

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
