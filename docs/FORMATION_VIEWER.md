# Formation Viewer

Alpha 0.4.1 introduces a read-only formation board for the PySide6 Match workspace.
It is inspired by the familiar lineup-building workflow of Hattrick managers, but uses
original HT Coach styling, components, colors and rendering.

## Architecture

```text
MatchPage
  -> FormationBoard
  -> FormationBoardViewModel
  -> FormationBoardMapper
  -> existing serializable MatchAnalysisResult
```

The board does not call the engine, optimize lineups, calculate player scores, access
persistence, or mutate match results. It renders immutable serializable view models
created from the existing match result data.

## Component Structure

```text
ht_coach_app/widgets/formation_board/
  formation_board.py
  pitch_widget.py
  player_card.py
  formation_layouts.py
  formation_board_models.py
  formation_board_styles.py

ht_coach_app/services/formation_board_service.py
```

`formation_layouts.py` owns normalized pitch coordinates. `formation_board_service.py`
maps match results into board view models. Widgets only render and emit selection
events.

## Coordinate Model

Each supported formation has exactly eleven slots with normalized coordinates:

- `x` ranges from `0.0` to `1.0`.
- `y` ranges from `0.0` to `1.0`.
- Forwards are near the top.
- Midfielders are in the middle.
- Defenders are in the lower half.
- Goalkeeper is near the bottom.
- Left slots have lower `x` values than right slots.

Supported formations:

- 2-5-3
- 3-4-3
- 3-5-2
- 4-3-3
- 4-4-2
- 4-5-1
- 5-2-3
- 5-3-2
- 5-4-1

The slot layouts are derived from the centralized formation catalog in
`models.formations`; formation definitions are not duplicated in the UI.

## Player Cards

Cards are compact and show:

- shortened player name;
- position abbreviation;
- individual order;
- order side when relevant.

Cards support normal, hover, selected, recommended and empty-slot fallback states. Long
names are truncated on the card and preserved in the tooltip.

## Player Intelligence

Alpha 0.4.2 upgrades the read-only inspector into Player Intelligence. Selecting a card
shows a deterministic explanation of the player's profile, why the optimizer selected
the player, tactical contributions, limitations and closest same-role alternatives.

The board remains read-only. Selection does not rerun match analysis or any optimizer.
Alternatives are informational only and use player-score differences, not fabricated
win-probability deltas.

## Order And Side Labels

The board uses centralized display formatting:

- Goalkeeper (GK)
- Central Defender (CD)
- Wing Back (WB)
- Inner Midfielder (IM)
- Winger (W)
- Forward (F)
- Left
- Center
- Right
- Normal
- Offensive
- Defensive
- Towards Middle
- Towards Wing

Raw enum values such as `INNER_MIDFIELDER` or `TOWARDS_WING` are not shown to users.

## Accessibility

Player cards are focusable buttons. Mouse click, Enter and Space select a card. Escape
or clicking the empty pitch area clears selection where practical.

## Restored Results

The Formation Viewer works with newly generated analysis results and persisted results.
It regenerates board view models from serializable match result data and does not
persist Qt widgets or graphics objects. Missing optional player detail fields display a
clean unavailable state instead of blocking the result view.

## Match Page Integration

The Match result area now uses local tabs:

- Formation Board
- Comparison
- Detailed XI

Formation Board is the default active view. Comparison and Detailed XI remain available
for dense inspection and accessibility. Switching the displayed formation uses already
analyzed result data and does not rerun optimization.

If board rendering fails, the Match page keeps the comparison and Detailed XI tabs
available and shows a recoverable board error message.

## Design Tokens

Formation Viewer starts a small visual token set for:

- pitch background;
- pitch lines;
- cards;
- selected cards;
- recommended borders;
- primary text;
- secondary text;
- warning/risk;
- positive/advantage;
- neutral states;
- spacing;
- border radius.

These tokens are centralized in `formation_board_styles.py` and should be reused by
future board-related widgets.

## Future Hattrick-inspired lineup editing workflow

Later Alpha 0.4 milestones can evolve the read-only board into an editing workspace:

- roster panel on the left;
- pitch in the center;
- inspector and impact panel on the right;
- drag from roster to slot;
- swap players;
- move a player between valid slots;
- remove a player from the pitch;
- change order using card controls;
- calculate lineup delta;
- reset to optimized recommendation.

This milestone only prepares stable slot IDs and player IDs. It does not implement drag
and drop, disabled fake drag behavior, or what-if recalculation.
