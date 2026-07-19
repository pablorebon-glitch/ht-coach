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

Alpha 0.4.2.1 compacts the normalized tactical lines while preserving their thirds and
left/center/right meaning. Alpha 0.4.3.1 centralizes pitch geometry into a shared model
containing the playing field, external drawing bounds, goals, penalty areas, goal areas,
center circle and corner arcs. The pitch fits a centered 68:105 field rectangle into the
available board area while reserving drawing space for both goals.

Goals are centered on the top and bottom goal lines and drawn outside the playing field.
Corner arcs are anchored at the exact four pitch corners and curve inward toward the
field. Resize handlers, painting and geometry tests consume the same source geometry;
they do not define formation-specific coordinates.

## Player Cards

Cards are compact and show:

- shortened player name;
- position abbreviation;
- individual order;
- order side when relevant.

Cards support normal, hover, selected, recommended and empty-slot fallback states. Long
names are truncated on the card and preserved in the tooltip.

Card width is bounded by the closest pair of slots on the current tactical line as well
as global readable minimum/maximum sizes. Height scales with width. Cards remain inside
the pitch and do not alter formation geometry during selection or resizing.

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

## Compact Tactical Workspace

Alpha 0.4.2.1 places the pitch and Player Intelligence in a horizontal splitter with an
initial 65/35 proportion and usable minimum pane widths. The pitch never scrolls. Player
Intelligence uses an internal vertical scroll area, and Technical Details starts
collapsed, so long explanations cannot force the pitch smaller.

Successful and restored analyses collapse Analysis Setup but keep its header available.
The user can show or hide setup again without clearing results, resizing the lower
workspace destructively or starting optimization. The Match page owns outer vertical
scrolling when content is taller than the window, so the board keeps a practical minimum
height instead of shrinking into a miniature. The supported desktop target is 1280x720
and above, with explicit checks at 1366x768, 1600x900 and 1920x1080.

Alpha 0.4.3 makes the board editable through Workspace replacements. Applied
replacements are visually marked and can be evaluated through fixed-lineup Workspace
recalculation without replacing the editable lineup with a newly optimized XI.

Alpha 0.4.4 adds drag-and-drop lineup editing to the same Workspace model. Starting
players can be dragged onto other occupied slots to swap assignments, and replacement
candidates can be dragged onto an occupied slot to perform the same replacement that a
click would create. Alpha 0.4.5 commits valid edits immediately and schedules automatic
fixed-lineup recalculation, so there are no Apply, Cancel or manual Recalculate buttons.
The board stores stable slot IDs and workspace revisions in drag payloads, so stale
gestures are rejected safely.

Alpha 0.4.4.1 adds an integrated Bench panel beside the pitch. Bench is derived from the
loaded roster minus the currently displayed Workspace Lineup. Bench players can be
dragged onto occupied lineup slots, and starters can be dragged onto Bench player cards;
both directions normalize to the same immediate replacement exchange. The Bench has its
own internal scroll area, while Player Intelligence remains focused on explanations and
closest alternatives.

Alpha 0.4.5 reduces the pitch footprint, preserves Match-page scroll position across
selection and automatic result refreshes, and keeps Formation Board as the default local
result tab. Automatic workspace recalculation uses fixed-lineup evaluation and stale
result protection by Workspace revision; it never reruns lineup optimization after a
manual edit.

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

Later Alpha milestones can continue evolving the board into a broader editing workspace:

- roster panel on the left;
- pitch in the center;
- inspector and impact panel on the right;
- drag from roster to slot;
- move a player between valid slots;
- remove a player from the pitch;
- change order using card controls;
- calculate lineup delta;
- reset to optimized recommendation.

Alpha 0.4.5 implements immediate pitch-slot swaps, Bench exchanges and automatic
fixed-lineup recalculation. It does not implement order editing, substitutes/match plans
or a full Decision Delta system.
