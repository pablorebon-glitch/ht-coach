# Interactive Workspace

Alpha 0.4.3 introduces the HT Coach Workspace: an editable tactical layer on top of the
stable match recommendation.

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
- replacement preview;
- modification history;
- redo stack reserved for future use.

The dirty flag is derived from history. Reset creates a fresh editable copy from the
original recommendation and clears selection, preview and pending modifications.

## Editing Lifecycle

1. Select a player on the Formation Board.
2. Player Intelligence updates for the selected player.
3. Replace Player appears with compatible same-role candidates.
4. Choose one replacement to create a preview.
5. Review current player, replacement player, role and player score difference.
6. Apply Replacement modifies only the workspace lineup.
7. Recalculate Analysis must be clicked explicitly to run the existing analysis pipeline.

No probability, xG, tactic, Decision Lab or Decision Delta value changes during preview
or apply. Those values remain tied to the last successful optimizer result.

## Replacements

Available replacements reuse existing `PlayerAnalyzer.rank_players` for the selected
position and side. The current player and players already in the workspace lineup are
excluded. Up to five compatible players are shown in deterministic score/name order.

## Workspace Status

The board shows a compact status indicator:

- Original Recommendation: no workspace edits.
- Unsaved Changes: a replacement preview exists.
- Modified Workspace - Ready to Recalculate: at least one replacement was applied.

## Reset

Reset Workspace restores:

- original player assignments;
- orders and sides from the recommendation;
- selected player;
- replacement preview;
- dirty state.

Reset does not recalculate.

## Recalculate

Recalculate Analysis emits the same Match analysis request used by Analyze Match. It runs
through the existing worker, service and optimizer pipeline, then refreshes Decision Lab,
Player Intelligence, comparison, Detailed XI and Formation Board from the new result.

Recalculation is never automatic.

## Future Work

The workspace model reserves history and redo state so later milestones can add:

- Undo;
- Redo;
- drag and drop;
- Decision Delta;
- what-if comparison against the original recommendation.

Alpha 0.4.3 deliberately does not include drag and drop, automatic recalculation,
Decision Delta or animated interactions.
