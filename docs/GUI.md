# HT Coach Alpha 0.2 GUI Guide

## GUI Goal

HT Coach Alpha 0.2 should feel like a focused desktop coaching tool: calm, structured,
fast to scan, and reliable during long calculations.

The GUI should be built with PySide6. The existing Tkinter app is useful as workflow
reference, but it should not define the long-term architecture or receive new Alpha 0.2
features.

## Primary Navigation

Use a main window with:

- Left navigation rail.
- Central stacked content area.
- Persistent status area.
- Optional top action bar for screen-specific primary actions.

Recommended navigation items:

1. Dashboard
2. Squad
3. Opponents
4. Match
5. Reports
6. Settings

This structure supports future growth better than a single tab notebook.

## Main Window Layout

```text
+---------------------------------------------------------------+
| HT Coach                                      status / actions |
+---------------+-----------------------------------------------+
| Dashboard     |                                               |
| Squad         |              Current Screen                    |
| Opponents     |                                               |
| Match         |                                               |
| Reports       |                                               |
| Settings      |                                               |
+---------------+-----------------------------------------------+
| Ready                                                         |
+---------------------------------------------------------------+
```

## Views

### Dashboard View

Purpose:

- Give the user a quick overview of the current workspace.

Content:

- Loaded roster summary.
- Selected opponent.
- Latest recommendation summary.
- Shortcuts to primary workflows.

No marketing hero or decorative layout is needed. This is an operational tool.

### Squad View

Purpose:

- Import and inspect the player roster.

Content:

- CSV path selector.
- Load and reload buttons.
- Export visible rows button.
- Sortable player table with core skills, form, stamina, experience, leadership, TSI,
  salary and specialty.
- Search by player name.
- Minimum form and stamina filters.
- Specialty filter.
- Position ranking filter.
- Player detail panel with complete skills, best position and rankings by supported
  position.
- Player count and import status.
- Optional player detail panel.

Expected controls:

- File picker button.
- Refresh/load button.
- Sortable table columns.
- Search and filter controls.
- Position ranking selector.
- Export visible table action.
- Clear error display for invalid CSV.

### Opponents View

Purpose:

- Manage saved opponents.

Content:

- Opponent list.
- Opponent name field.
- Seven-sector rating editor.
- Save, new, duplicate, delete, and select actions.

Expected controls:

- List selection.
- Text input for name.
- Numeric rating inputs.
- Duplicate action.
- Confirmation dialog for delete.
- Validation messages for empty name or invalid rating.

### Match View

Purpose:

- Optimize lineup, orders, and tactic against a selected opponent.

Content:

- Players CSV selector and load status.
- Selected opponent selector.
- Formation checklist generated from the centralized formation catalog.
- Select All, Clear All, and Favorites controls. Favorites preserve the familiar
  3-5-2 and 4-5-1 starting point.
- Compact warning when many formations are selected.
- Analyze Match action.
- Progress indicator.
- Prominent recommended-result summary.
- Formation Board tab with a vertical pitch, compact player cards, formation switching
  across analyzed alternatives, click-to-inspect behavior, and original HT Coach styling.
- Player Intelligence inspector with profile label, coach's note, why-selected points,
  contribution bars, strengths, limitations, alternatives and technical details.
- Decision Lab section with recommendation, confidence badge, reasons, risks, tactical
  observations, sector matchup notes, and optimization gain breakdown.
- Formation comparison table with deltas versus the recommendation.
- Detailed XI table for inspection and accessibility.
- Probabilities, xG, possession, and tactic.
- Analysis metadata: opponent, CSV filename, player count, formations, and completion
  time.

Expected controls:

- File picker button.
- Load Players button.
- Opponent combo box.
- Formation checkboxes.
- Formation preset buttons.
- Primary Analyze Match button.
- Busy state while worker runs.
- Copy Summary and Copy Lineup actions.
- Copy Decision Lab action.
- Result table and recommended XI table inside the page.
- Formation Board, Comparison and Detailed XI result tabs.
- Empty, loading, success, and error states.

### Reports View

Purpose:

- Review recommendation summaries and prepare future exports.

Content:

- Latest match summary.
- Formation and lineup recommendation sections.
- Placeholder export action.

Expected controls:

- Report selector.
- Read-only summary panels.
- Future export button.

### Settings View

Purpose:

- Manage app-level preferences.

Content:

- Default data folder.
- Last CSV behavior.
- Theme preference.
- Diagnostics/log file location.

Settings should not expose engine internals unless they are stable user-facing options.

## Reusable Widgets

### RatingInputGrid

Seven numeric inputs:

- Left defense
- Central defense
- Right defense
- Midfield
- Left attack
- Central attack
- Right attack

Responsibilities:

- Render consistent labels.
- Validate numeric values.
- Convert between UI values and `TeamRatings`.
- Emit change signals.

### PlayerTable

Responsibilities:

- Display players.
- Support sorting.
- Support selection.
- Avoid embedding import logic.

### OpponentEditor

Responsibilities:

- Edit opponent name and ratings.
- Track dirty state.
- Expose save/delete/select signals.

### FormationResultTable

Responsibilities:

- Display formation score rows.
- Emit selected result.
- Keep display formatting out of engine code.

### MatchResultPanel

Responsibilities:

- Display high-level recommendation.
- Show win/draw/loss.
- Show expected goals and possession.
- Show tactic and tactic level.

### DecisionLabPanel

Responsibilities:

- Display the deterministic recommendation explanation.
- Show recommendation confidence as a badge, not a statistical certainty.
- List the highest-value reasons and meaningful risks.
- Show a compact top recommendation card, coaching-style reasons, meaningful risks,
  tactic-specific observations, sector matchup notes, and optimization impact.
- Keep copy-ready text plain and readable.

### LineupTable

Responsibilities:

- Display position, player, and order.
- Support copy/export later.

### FormationBoard

Responsibilities:

- Display the analyzed lineup on a vertical football pitch.
- Keep goalkeeper at the bottom, defenders below midfielders, midfielders in the middle
  and forwards at the top.
- Preserve left, center and right semantics.
- Render compact player cards with user-facing position, side and order labels.
- Support read-only player selection and Player Intelligence updates.
- Avoid engine, optimizer and persistence dependencies.

### PlayerIntelligencePanel

Responsibilities:

- Explain the selected player before showing raw attributes.
- Show deterministic profile, why-selected reasoning, tactical contribution bars,
  strengths, limitations and alternatives.
- Display score deltas as player-score differences, never win-probability deltas.
- Avoid chemistry, hidden relationships or unsupported game mechanics.
- Preserve clean unavailable states for restored results without roster data.

## Controllers

Controllers connect views to application behavior.

Suggested controller mapping:

- `SquadController` for `SquadView`.
- `OpponentController` for `OpponentsView`.
- `MatchController` for `MatchView`.
- `ReportsController` for `ReportsView`.
- `NavigationController` for main window routing.

Controller rules:

- Accept signals from views.
- Call services.
- Update state.
- Tell views what to render.
- Do not calculate ratings or probabilities.

## Services

Services keep workflows reusable and testable.

Suggested services:

- `RosterService`
- `OpponentService`
- `MatchWorkspaceService`
- `ReportService`
- `SettingsService`

Service rules:

- Call stable engine APIs.
- Map engine outputs to app view models.
- Normalize errors.
- Avoid direct widget imports.

## State Management

Use explicit state objects and Qt signals.

Recommended state:

- `AppState`
- `RosterState`
- `OpponentState`
- `OptimizationState`

State rules:

- Views read display state through controllers.
- Controllers update state after service results.
- Workers emit results back to controllers.
- No widget should be the only source of important application state.

## Persistence

Initial persistence should use JSON repositories.

Recommended files:

- `opponents.json`
- `match_workspace.json`
- `match_last_result.json`
- `settings.json`
- `recent_files.json`

Persistence rules:

- Store user data outside engine folders.
- Include schema versions once data evolves.
- Keep persistence format hidden behind repositories.
- Do not let views read or write JSON directly.
- Persist only serializable view-model data for the last successful match analysis.

## Background Work

Formation and match optimization must run outside the UI thread.

Recommended pattern:

- Controller creates request.
- Service prepares callable work.
- Worker runs optimization.
- Worker emits success or failure.
- Controller updates state.
- View re-renders.

UI requirements:

- Disable duplicate optimize actions while running.
- Show busy state.
- Preserve the last successful result until a new result is ready.
- Restore the last successful result when the app reopens.
- Display errors without crashing.

## UI Consistency

Use a restrained desktop style:

- Consistent spacing.
- Tables for dense data.
- Side panels for details.
- Clear primary actions.
- Avoid decorative cards inside cards.
- Avoid oversized landing-page patterns.
- Keep labels short and operational.

Preferred patterns:

- Tables for comparison.
- Split panes for list plus detail.
- Numeric spin boxes or validated line edits for ratings.
- Combo boxes for saved opponent selection.
- Dialogs only for confirmation or focused edits.

## Error Handling

All user-facing errors should be clear and actionable.

Examples:

- "Select a players.csv file."
- "Select at least one formation."
- "Opponent name is required."
- "All opponent ratings must be numeric."
- "Optimization failed. See diagnostics for details."

Technical tracebacks should go to logs, not modal dialogs.

## Accessibility And Usability

Minimum expectations:

- Keyboard navigation for primary forms.
- Visible focus states.
- Readable table typography.
- No text clipped inside buttons.
- No UI freeze during optimization.
- Sensible empty states.

## GUI Non-Goals For Alpha 0.2

- Web UI.
- Real-time cloud sync.
- Animated dashboards.
- Custom rendering engine.
- Reimplementation of engine calculations in the UI layer.
