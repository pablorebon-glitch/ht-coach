# Interactive Workspace

Alpha 0.4.4 extends the HT Coach Workspace: an editable tactical layer on top of the
stable match recommendation with click replacement and drag-and-drop lineup editing.

## Concept

The Match page now separates two lineups:

- Recommended Lineup: the immutable optimizer result.
- Workspace Lineup: the editable copy shown on the Formation Board.

The original recommendation is never modified. Manual changes are kept in workspace
state until the user explicitly recalculates.

## Architecture

```text
FormationBoard
  -> WorkspaceService
  -> WorkspaceState
  -> FormationBoardViewModel copies
  -> existing PlayerAnalyzer ranking
```

`ht_coach_app/workspace/` is UI-independent. It owns the editing model, dirty state,
replacement previews and future undo/redo history shape. Widgets render this state and
emit user intent; they do not calculate replacement rules.

## Workspace Model

Workspace state contains:

- original boards;
- editable workspace boards;
- current formation;
- selected player;
- replacement or swap preview;
- modification history;
- redo stack reserved for future use.
- evaluation state: original, pending recalculation, or evaluated.
- revision number used to reject stale drag previews safely.

The dirty flag is derived from history. Reset creates a fresh editable copy from the
original recommendation and clears selection, preview and pending modifications.

## Editing Lifecycle

1. Select a player on the Formation Board.
2. Player Intelligence updates for the selected player.
3. Replace Player appears with compatible same-role candidates.
4. Choose one replacement to create a preview, or drag a replacement candidate onto an
   occupied slot.
5. Review current player, replacement player, role and player score difference.
6. Apply Change modifies only the workspace lineup.
7. Recalculate Analysis must be clicked explicitly to evaluate the current Workspace
   Lineup.

No probability, xG, tactic, Decision Lab or Decision Delta value changes during preview
or apply. Those values remain tied to the last successful result until Recalculate
Analysis is pressed.

## Replacements

Available replacements reuse existing `PlayerAnalyzer.rank_players` for the selected
position and side. The current player and players already in the workspace lineup are
excluded. Up to five compatible players are shown in deterministic score/name order.

Click replacement and drag replacement use the same workspace service operation. Drag
payloads carry stable domain data: player ID, source type, source slot when applicable,
formation and workspace revision. They never depend on visible button text.

## Drag and Drop

Alpha 0.4.4 supports two drag paths:

- starting player to starting player: previews a slot swap;
- replacement candidate to starting slot: previews a role-compatible replacement.

The preview does not mutate the lineup. Apply Change commits the preview, Cancel Change
or Escape clears it. A formation switch clears any active preview. If the workspace
revision changed after the drag began, the apply is rejected with a safe message and the
user can retry the gesture.

Slots remain the tactical source of truth. When two players are swapped, the player moves
but the destination slot keeps its position, side, order and normalized pitch coordinate.

## Workspace Status

The board shows a compact status indicator:

- Original Recommendation: no workspace edits.
- Replacement Preview: a replacement candidate is selected but not applied.
- Swap Preview: two occupied slots are selected for a pending swap.
- Modified Workspace - Pending Recalculation: at least one replacement was applied.
- Evaluated Workspace: current metrics were recalculated for the Workspace Lineup.

## Reset

Reset Workspace restores:

- original player assignments;
- orders and sides from the recommendation;
- selected player;
- replacement or swap preview;
- dirty state.

Reset does not recalculate.

## Recalculate

Recalculate Analysis sends the current Workspace Lineup to the Match worker as a fixed
lineup. The application layer rebuilds an engine `Lineup` from the editable board,
calculates ratings with the existing `TeamRater`, evaluates tactics with the existing
`TacticOptimizer`, maps the result to the same serializable Match view models, and then
refreshes Decision Lab, Player Intelligence, comparison, Detailed XI and Formation Board.

Workspace recalculation deliberately bypasses lineup optimization. It does not invent
metrics and does not change rating, probability, xG, tactic, order or Decision Lab
formulas.

Recalculation is never automatic.

After recalculation, the Workspace Lineup keeps its applied player assignments and the
original recommendation remains available as the Reset Workspace baseline.

## Match Layout

Alpha 0.4.3.1 keeps Analysis Setup as a persistent collapsible section. It is expanded
before the first analysis, collapses after success, and can be shown or hidden without
rerunning analysis, clearing results or changing workspace state.

The compact match summary now shows only match context such as `Opponent: Rival FC` and
`Formations: 2`. CSV filename, player count, completion timestamp, copy actions and the
old Edit Analysis button are removed from the visible summary.

The Match page uses an outer vertical scroll area so the Formation Board can keep a
useful minimum height. The pitch itself does not scroll internally.

## Future Work

The workspace model reserves history and redo state so later milestones can add:

- Undo;
- Redo;
- Decision Delta;
- what-if comparison against the original recommendation.

Alpha 0.4.4 deliberately does not include automatic recalculation, Decision Delta or
animated interactions.
