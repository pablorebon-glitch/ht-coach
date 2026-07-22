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

## Shared UX Patterns

Alpha 0.5.5 introduces a lightweight design system under
`ht_coach_app/ui/design_system/`.

- Spacing, typography, colors and metrics are centralized.
- `StatusBadge` is used for semantic statuses such as readiness, urgency,
  availability and actions.
- `EmptyState` replaces blank panels for no-data, loading and recoverable states.
- Shared table configuration standardizes row height, selection, header behavior and
  scrolling.
- Page headers can show a compact current-source indicator so loaded CSV paths remain
  visible without dominating the workspace.
- Squad preserves the selected tab as presentation state without rerunning analysis.

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
- Build an opponent-independent Ideal XI for roster review before match preparation.

Content:

- CSV path selector.
- Load and reload buttons.
- No primary Export button; export service remains available outside the main Squad
  Builder workflow.
- Five tabs: Ideal XI, Players, Evolution, Weekly Planner and Transfer Planner.
- Ideal XI tab with a top formation selector containing Auto and every supported
  formation from the centralized catalog.
- Auto mode evaluates every supported formation and displays the best roster fit.
- Formation Board reused from the Match workspace for the Ideal XI pitch; no second
  pitch widget is introduced.
- Assisted Lineup controls on the Formation Board support click-to-click starter swaps,
  Bench exchanges, automatic order selection and Restore Optimized Lineup without
  requiring drag-and-drop.
- Best Formations side panel with sorted scores and deltas versus the best result.
- Summary with best formation, overall score, confidence and reason.
- Squad Identity panel that separates Identity, Strengths, Weaknesses, Tactical
  Readiness and Formation Affinity.
- Identity explanation that describes what the squad naturally does well without
  recommending match tactics.
- Tactical Readiness entries for Normal, Attack in the Middle, Attack on Wings, Play
  Creatively, Pressing, Counter-Attacks and Long Shots, with why suitable, strengths,
  limitations, main contributors and compatible formations.
- Formation Affinity for every supported formation, reusing existing Squad Builder
  formation optimization results.
- Squad availability selector with Current Available Squad as the default and Full
  Strength Squad as a clearly labeled theoretical simulation.
- Squad Health panel showing available player count, unavailable starters, affected
  areas and severity.
- Unavailable players table with name, status, injury value, best role and expected
  role when available.
- Availability impact comparing Current Available Squad against Full Strength Squad
  using already evaluated outputs.
- Positional coverage by broad role: Goalkeeper, Central Defense, Wing Defense,
  Midfield, Winger and Forward.
- Availability column and filter in the Players tab.
- Evolution tab for long-term squad planning without overloading the Ideal XI workflow.
- Planning Horizon selector with Current, Short Term and Medium Term perspectives.
- Current Training Focus selector with Unknown as the safe default.
- Age Structure section with textual averages, youngest/oldest player, age bands and
  broad role distribution.
- Succession Map showing full-strength starter, current available starter, backup,
  potential successor, readiness, operational risk and structural risk.
- Development Candidates, Training Alignment, Identity Continuity, Priority Risks and
  Player Evolution Details sections.
- Evolution filters for at-risk positions, no successor, development candidates,
  veterans, training-aligned players and key dependencies.
- Weekly Planner tab for Playmaking training priorities, current-week coverage and a
  second-match lineup plan.
- Weekly Planner controls include active training, fixed formation, Generate Plan,
  Record Played Lineup and Use This Lineup.
- Weekly Planner uses one unified weekly-player table with player, age, best training
  position, simplified priority, training status, confirmed, planned, remaining and
  availability columns.
- Weekly Planner priority choices are intentionally compact: 100%, 50% and No priority
  in English, or 100%, 50% and Sin prioridad in Spanish. Older saved priority values
  are mapped into those three UI choices.
- Weekly Planner training status uses accessible symbols: check mark for already
  trained, open circle for will train in the generated plan and dash for will not train.
- Weekly Planner shows a visible first-match record card after recording, with Edit,
  Replace and Delete actions.
- Weekly Planner second-match output uses the shared Formation Board and requires an
  explicit Use This Lineup action before copying the proposal into the Squad Ideal XI
  board.
- Weekly Planner Generate Plan now uses the Planner Execution Engine: ordinary 100%/50%
  priority conflicts still produce a best-effort lineup, populated bench, automatic
  orders, coverage updates, internal competitive cost and conflict explanations. Only
  truly impossible cases such as no available players, unsupported formation or no
  valid goalkeeper leave the proposal empty.
- Formation Board bench and player-details side panels can be collapsed in Match,
  Squad and Weekly Planner. Collapsing releases real width while preserving selection
  and the existing detail widgets.
- Weekly Planner warnings explain assumed 90-minute exposure, hard conflicts and
  internal competitive cost without presenting it as a Hattrick rating projection.
- Transfer Planner tab that turns Squad Evolution outputs into abstract player-profile
  recommendations for recruitment planning.
- Transfer Planner constraints for planning objective, budget tier, age strategy,
  training compatibility preference and specialty preference.
- Transfer Planner priority table showing role, urgency, need type, target role,
  recommended action and internal-solution status.
- Transfer Planner detail panel split into semantic sections: recommendation summary,
  recommended profile, why this transfer, expected impact, no-action scenario,
  alternative profiles and technical details.
- Transfer Planner priority rows use semantic badges for urgency and recommended action
  so Buy Now, Develop Internally and Monitor are easier to scan.
- Transfer recommendations are profile-based only. They do not name real players, use
  live Transfer Market data, estimate exact prices or claim exact future performance
  deltas.
- Transfer Planner roles, positions, target roles, skills, specialties, formations,
  tradeoffs, impact dimensions and no-action scenarios must pass through the
  localization layer before reaching the UI.
- Transfer Planner presentation strings are composed by the application presenter, not
  by the planner. Language changes refresh the visible sections and priority table from
  the cached view result without rerunning analysis or changing profile values.
- Transfer Planner lists use localized conjunctions, so English copy uses `and` and
  Spanish copy uses `y` in readable multi-value sentences.
- Player Intelligence inspector inside the Formation Board for selected Ideal XI
  players, including why recommended, position fit, role and alternatives.
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
- Auto/manual formation selector for Ideal XI.
- Best Formations ranking table.
- Tactical Readiness selector and detail display.
- Formation Affinity table.
- Availability mode selector.
- Availability filter in the Players table.
- Transfer Planner selectors for objective, budget, age strategy, training fit and
  preferred specialty.

### Opponents View

Purpose:

- Manage saved opponents.

Content:

- Opponent list.
- Opponent name field.
- Seven required sector ratings plus optional indirect defense and indirect attack
  ratings for Hattrick imports that include them.
- Ratings are shown in Hattrick order: Midfield, Right Defense, Central Defense, Left
  Defense, Right Attack, Central Attack, Left Attack, Indirect Set Pieces Defense and
  Indirect Set Pieces Attack.
- Manual rating inputs accept comma and point decimals in any UI language, then display
  values using the active application language.
- Paste Ratings imports copied Hattrick table text through a localized preview. Apply
  updates only parsed fields; Cancel and invalid clipboard data leave the form
  unchanged.
- Clipboard import supports Spanish and English Hattrick labels, ignores average-rating
  rows, and only maps generic Defense/Attack rows inside the Indirect Set Pieces
  section.
- Save, new, duplicate, delete, and select actions.

Expected controls:

- List selection.
- Text input for name.
- Numeric rating inputs.
- Paste Ratings action.
- Clipboard import preview with Apply and Cancel.
- Duplicate action.
- Confirmation dialog for delete.
- Validation messages for empty name or invalid rating.

### Match View

Purpose:

- Optimize lineup, orders, and tactic against a selected opponent.

Content:

- Players CSV selector and load status.
- Squad availability selector with Current Available Squad as the default and Full
  Strength Squad as a clearly warned simulation mode.
- Selected opponent selector.
- Formation checklist generated from the centralized formation catalog.
- Select All, Clear All, and Favorites controls. Favorites preserve the familiar
  3-5-2 and 4-5-1 starting point.
- Compact warning when many formations are selected.
- Analyze Match action.
- Progress indicator.
- Compact recommended-result summary and analysis metadata row.
- Availability impact note showing unavailable player count and warning when Full
  Strength results include unavailable players.
- Analysis inputs that collapse after success and reopen without rerunning analysis.
- Persistent collapsible Analysis Setup with a visible toggle. Showing or hiding setup
  preserves selected values, current results and Workspace state.
- Formation Board tab with a vertical pitch, compact player cards, integrated Bench,
  formation switching across analyzed alternatives, click-to-inspect behavior,
  one-click workspace replacement actions, and original HT Coach styling.
- Interactive Workspace editing where valid click and drag actions commit immediately
  to the Workspace Lineup, optimize affected individual orders and schedule bounded
  fixed-lineup refresh. Restore Optimized Lineup remains the only global edit action.
- Click-to-click starter swaps use the same canonical operation as drag-and-drop.
  Selecting the same player cancels selection, Escape cancels selection, and invalid
  destinations preserve the lineup.
- Manual edits show `Lineup manually adjusted`; manual slot choices are treated as
  intentional and are not contradicted by visible position recommendations.
- Automatic order selection uses only supported domain order configurations, preserves
  current valid orders on ties and does not imply Hattrick decimal ratings.
- Bench panel with compact focusable cards, deterministic roster-minus-lineup derivation
  and internal scrolling. Clicking a Bench player and then a starter, or selecting a
  starter and clicking a Bench player, performs the same immediate exchange.
- Player Intelligence inspector with profile label, coach's note, why-selected points,
  contribution bars, strengths, limitations, alternatives, collapsed technical details
  and internal overflow scrolling.
- Compact Decision Lab row with localized recommendation confidence, explicit
  recommendation-support wording, and play-to-win, secure-draw and avoid-defeat
  perspectives derived from existing result data. Recommendation support is not
  presented as a match probability. Full copy output remains available.
- Change Analysis panel after Workspace recalculation, comparing the previous evaluated
  Workspace to the current evaluated Workspace with last change, position fit, team
  impact, changed sectors only and a deterministic summary.
- Match Intelligence panel with team profile, opponent profile, tactical focuses, key
  opportunities, key risks and a compact matchup matrix. When HT Coach internal team
  ratings and imported Hattrick decimal opponent ratings are not directly comparable,
  the UI hides direct margins, advantage classes and difference-based signals while
  retaining profile and possession context.
- Opponent Rating Calibration panel that labels HT Coach internal ratings and imported
  Hattrick decimal ratings by source scale and only shows direct advantages when the
  compared values share the same scale. If scales differ, the difference column is not
  shown.
- Decision Lab, Match Intelligence, Opponent Rating Calibration and Match Analysis use
  shared collapsible sections with independent persisted state, brief summaries,
  keyboard-accessible headers and localized expand/collapse labels.
- Alpha 0.5.7.1a rebuilds the collapsible section as a simple Qt header/body
  component. The header is the only visible element when collapsed, the existing body
  widget is hidden but not destroyed, expanded sections use natural body `sizeHint`,
  and individual sections do not receive vertical stretch. The Match parent layout keeps
  analysis sections in order and reserves any leftover space for the page/scroll area
  rather than for collapsed cards.
- First-launch Match section defaults are: Decision Lab collapsed, Match Intelligence
  collapsed, Opponent Rating Calibration collapsed and Match Analysis expanded.
  Previously saved `match_section_states` values continue to override those defaults.
- This rebuilt component is applied only to the four Match analysis sections in
  0.5.7.1a. Player details, bench and planner-specific panel integrations remain
  separate work and should not be coupled to this component until the Match section
  behavior is stable.
- Rating Engine Alignment diagnostics classify current TeamRater values as internal
  contribution totals. The normal Match UI must not display own-team Hattrick decimal
  ratings unless a future evidence-backed conversion is introduced.
- Tactical Advisor panel with three to five ranked, informational recommendations
  derived from the current evaluated Workspace.
- Formation comparison table with deltas versus the recommendation.
- Detailed XI table for inspection and accessibility.
- Probabilities, xG, possession, and tactic.
- Analysis metadata: opponent, CSV filename, player count, formations, and completion
  time in copy/export surfaces. The visible compact summary keeps only high-value match
  context such as opponent and formation count.

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

After analysis, the Match view prioritizes a growing horizontal tactical workspace.
Formation Board starts at approximately 65% width and Player Intelligence at 35%; the
user can resize both panes. The pitch maintains its 68:105 field ratio and never scrolls
internally. The Match page scrolls vertically when content is taller than the window,
letting the board keep a useful minimum height. The practical minimum supported
application size is 1280x720. Below this size, cards continue to scale and elide text
without changing tactical geometry.

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

- Language selector with English and Spanish.
- Advisor verbosity selector with Simple and Detailed modes.
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

### MatchIntelligencePanel

Responsibilities:

- Display deterministic tactical interpretation from already evaluated Match Workspace
  data.
- Show exactly three tactical focus items.
- Show our profile and opponent profile without exposing raw engine objects.
- Show key opportunities and risks as localized text.
- Render a compact matchup matrix for our attacks against opponent defenses and
  opponent attacks against our defenses.
- Highlight best and worst attacking routes with compact markers.
- Avoid recalculating ratings, probabilities, xG or optimizer results.

### LineupTable

Responsibilities:

- Display position, player, and order.
- Support copy/export later.

### FormationBoard

Responsibilities:

- Display the analyzed lineup on a vertical football pitch.
- Keep goalkeeper at the top, then defenders, midfielders and forwards in Hattrick
  lineup-editor order.
- Preserve left, center and right semantics.
- Render compact player cards with user-facing position, side and order labels.
- Support player selection, Player Intelligence updates and immediate workspace
  replacements.
- Support starter-to-starter click swaps, Bench-to-starter click replacements,
  starter-to-Bench drag exchanges and accessible non-drag editing paths.
- Show assigned position, automatically selected order and concise order-change feedback
  without permanent Apply buttons.
- Show the finalized optimized orders immediately on first render and after roster
  reloads; do not show an intermediate all-Normal lineup when order evaluation has not
  run yet.
- Preserve manual player-slot assignments after Match recalculation. Refreshes may update
  tactic metadata, sector totals and analysis panels, but they must not move players back
  to the original recommendation.
- Distinguish immutable Recommended Lineup state from editable Workspace Lineup state.
- Show Original Recommendation, Lineup manually adjusted, Updating Analysis,
  Analysis updated and error states.
- Emit workspace-modified intent for the controller to debounce and recalculate without
  calling the engine directly.
- Preserve Match viewport state during automatic refresh, including scroll position,
  active result tab and selected player where the player is still present.
- Reuse the Match result tab hierarchy, Formation Board, Pitch widget and player cards
  during automatic refresh. Incremental updates should repaint changed labels, orders,
  card state and analysis panels without rebuilding the pitch or resetting splitter
  geometry.
- Preserve splitter sizes across analysis refreshes. Pitch dimensions should change only
  because of window, splitter or DPI changes, not because recalculated analysis returned.
- Own Hattrick-oriented full-pitch scaling, normalized slot coordinates, card
  containment and the compact formation/tactic footer.
- Keep reusable pitch and inspector layout behavior outside `MatchPage`.
- Avoid engine, optimizer and persistence dependencies.

### PlayerIntelligencePanel

Responsibilities:

- Explain the selected player before showing raw attributes.
- Show deterministic profile, why-selected reasoning, tactical contribution bars,
  strengths, limitations and alternatives.
- Display score deltas as player-score differences, never win-probability deltas.
- Avoid chemistry, hidden relationships or unsupported game mechanics.
- Preserve clean unavailable states for restored results without roster data.

### ChangeAnalysisPanel

Responsibilities:

- Display the latest Workspace change after automatic recalculation.
- Compare old and new calculated win, draw and loss values.
- Show only sectors whose calculated ratings changed.
- Use deterministic interpretation thresholds.
- Avoid calling engine code or duplicating Decision Lab reasoning.

### TacticalAdvisorPanel

Responsibilities:

- Show ranked Action, Observation and Warning cards from the deterministic advisor
  engine.
- Display title, category and confidence for every card.
- Display estimated win-probability impact only for actionable recommendations with a
  measurable evaluated before/after delta.
- Hide explanations in Simple mode and show them in Detailed mode.
- Never auto-apply changes.
- Avoid presenting weak sectors, low possession or attack imbalance as commands unless
  an evaluated formation or Workspace change improves the result.
- Use localized strings for all labels and recommendation copy.

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
- `ChangeAnalysisService`
- `LocalizationService`
- `RecommendationEngine`
- `ReportService`
- `SettingsService`

Service rules:

- Call stable engine APIs.
- Map engine outputs to app view models.
- Normalize errors.
- Avoid direct widget imports.
- Return user-facing text through the localization layer where practical.

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
- `app_settings.json`
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
