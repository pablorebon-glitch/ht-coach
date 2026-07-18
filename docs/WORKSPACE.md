# Interactive Workspace

Alpha 0.4.5 turns the HT Coach Workspace into a one-click tactical lab: lineup edits
commit immediately, fixed-lineup analysis updates automatically, and Reset Workspace is
the only global edit action.

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

## Keyboard Replacement

Drag is not the only editing route. Select a lineup slot, focus or click a Bench card,
then press Enter, Space, or click to commit that replacement. The reverse sequence also
works: select a Bench player, then click a starter.

## Workspace Status

The board shows a compact status indicator:

- Original Recommendation: no workspace edits.
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

The debounce coalesces rapid edits. A returning result is applied only when its captured
Workspace revision still matches the latest requested revision.

After recalculation, the Workspace Lineup keeps its committed player assignments and the
original recommendation remains available as the Reset Workspace baseline.

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
- Decision Delta;
- what-if comparison against the original recommendation.

Alpha 0.4.5 deliberately does not include a full Decision Delta system or animated
interactions.
