# HT Coach Alpha Roadmap

## Current Position

HT Coach has a stable optimization engine and an early desktop surface. Alpha 0.2 starts
the transition from a functional prototype to a professional PySide6 desktop
application.

The roadmap protects the engine and moves product work into the application layer.

## Guiding Principles

- Preserve engine behavior unless a confirmed bug is found.
- Build the desktop app around clear controllers, services, views, widgets, state, and
  persistence.
- Keep each milestone shippable.
- Prefer simple JSON persistence until user data becomes relational.
- Make long-running optimization visible and non-blocking.

## Alpha 0.2 Milestones

### Milestone 1: Architecture Foundation

Goal: define and scaffold the desktop application boundary.

Deliverables:

- `docs/ARCHITECTURE.md`
- `docs/GUI.md`
- `docs/ROADMAP.md`
- PySide6 package plan
- Decision to freeze engine calculation changes

Acceptance criteria:

- The intended folder structure is documented.
- Dependency direction is clear.
- No GUI implementation is required yet.

### Epic 1: PySide6 Shell

Goal: create the empty professional desktop frame.

Deliverables:

- `ht_coach_app/main.py`
- `ht_coach_app/app.py`
- Main window
- Left navigation
- Stacked content area
- Status area
- Toolbar
- Application icon support
- Empty page classes for Dashboard, Squad, Opponents, Match, Reports, and Settings
- Theme bootstrap
- Navigation controller

Acceptance criteria:

- The app launches.
- Navigation switches between placeholder screens.
- Navigation does not open new windows.
- Each page is its own `QWidget` class.
- Business workflows stay out of widgets.
- No engine behavior is changed.

### Epic 2: State And Services

Goal: introduce application state and use-case services.

Deliverables:

- `AppState`
- `RosterState`
- `OpponentState`
- `OptimizationState`
- `RosterService`
- `OpponentService`
- `OptimizationService`
- Initial view model classes

Acceptance criteria:

- Controllers can update shared state.
- Services isolate engine and persistence calls from views.
- Unit tests cover core service behavior.

### Epic 3: Persistence

Goal: persist user-owned app data reliably.

Deliverables:

- Local app data path resolver
- Opponent repository
- Settings repository
- Recent files repository
- JSON schema version field

Acceptance criteria:

- Saved opponents survive app restart.
- Last CSV path can be restored.
- Invalid or missing JSON fails gracefully with a user-safe message.

### Epic 4: Squad Screen

Goal: port squad loading to the PySide6 app.

Deliverables:

- Squad view
- CSV file picker
- Player table
- Import status
- Recent CSV path support
- Search, form, stamina, specialty, and position/ranking filters
- Position analysis using existing player analyzer APIs
- Player detail panel
- Export visible rows to CSV
- Squad-to-Match roster path synchronization through app events
- Squad Builder Ideal XI tab with Auto formation evaluation across the full formation
  catalog, Best Formations ranking, Squad Identity, reused Formation Board and
  integrated Player Intelligence.
- Squad Identity and Tactical Readiness panel replacing Preferred Style wording with
  descriptive identity, strengths, weaknesses, tactic capability readiness, formation
  affinity and main player contributors.
- Squad Health and Availability with Current Available Squad default, Full Strength
  simulation, centralized injury eligibility, health summary, unavailable player
  explanation, availability impact and positional coverage.
- Squad Evolution and Succession Planning with centralized age bands, planning
  horizons, full-strength versus current-available starter hierarchy, succession map,
  dependency analysis, development candidates, current training focus, training
  alignment, identity continuity and ranked planning risks.
- Transfer Planner with abstract player-profile priorities, configurable planning
  objective, budget tier, age strategy, training-fit preference, specialty preference,
  qualitative impact, alternatives, no-action scenario, localized semantic detail
  sections and readable list formatting.
- UX Consistency and Product Polish with shared PySide6 design tokens, semantic badges,
  card and empty-state patterns, standardized tables, localized main-screen copy,
  preserved Squad presentation state and documented accessibility/responsive guidance.
- Weekly Training Lineup Planner with Playmaking priorities, Sunday-Wednesday-Thursday
  week handling, minute-aware coverage, first-match records, second-match lineup
  planning, competitive-cost reporting and JSON persistence.
- Planner Execution Engine for Alpha 0.5.7.2: Generate Plan now acts as a solver,
  producing the strongest legal best-effort lineup when ordinary training-priority
  conflicts exist, then reporting unmet targets, coverage, bench, orders and internal
  competitive cost for review and explicit acceptance into Squad.

Acceptance criteria:

- Users can load `players.csv`.
- Player table supports sorting.
- Users can review the strongest roster-fit XI without selecting an opponent.
- Switching formation rebuilds the Ideal XI summary, pitch and player explanation.
- Squad Identity describes long-term roster capability without opponent context or
  match-tactic recommendations.
- Injured players from the `Lesiones` CSV field are excluded before Squad Builder
  optimization in Current Available mode and included only in Full Strength simulation.
- Import errors do not crash the app.
- Match receives roster path changes without restarting the app.
- No engine formulas or optimizer calculations are changed.
- Evolution planning risk remains separate from match-performance ratings and avoids
  exact retirement, future-skill, market-value or transfer-price predictions.
- Transfer Planner reuses Squad Evolution outputs and avoids live market data, real
  player recommendations, exact prices and exact future performance deltas.
- Transfer Planner presentation changes must stay in the desktop presenter layer and
  must not change planner ranking, generated profiles or analytical formulas.
- UX polish does not introduce a new analytical engine and does not change analytical
  meaning, thresholds, rankings, formulas or optimizer scoring.
- Weekly Training planning must reuse existing formation, ranking, lineup and order
  behavior, and must not alter engine formulas, rating calculations or probability
  calculations.
- Weekly Training priority conflicts must not empty the workspace when a legal lineup
  exists; they should be shown as warnings and explanations beside the generated team.

### Epic 5: Opponent Manager

Goal: make opponent management a first-class desktop workflow.

Deliverables:

- Opponents view
- Opponent list
- Rating editor
- Hattrick-order rating entry
- Clipboard import for copied Hattrick ratings
- Locale-tolerant decimal rating input
- Save, update, duplicate, delete, and select actions
- Repository/service/controller boundaries
- Validation feedback
- JSON persistence under the application data directory

Acceptance criteria:

- Users can maintain multiple opponents.
- Empty or invalid opponent names are rejected.
- Saved opponents are available to Match Analysis.
- Clipboard import supports partial data safely and does not overwrite missing fields.
- Opponent rating input improvements do not change rating calibration, cross-sector
  matchups, formulas, optimizers or probability calculations.
- No new opponent workflow is added to the legacy Tkinter app.

### Epic 6: Match Analysis

Goal: port the complete opponent optimization workflow.

Deliverables:

- Match Analysis view
- Players CSV selector and loaded player count
- Opponent selector
- Formation selector generated from the full supported catalog
- Squad availability selector using Current Available Squad by default and Full
  Strength Squad for simulation
- Select All, Clear All, and Favorites preset for 3-5-2 and 4-5-1
- Optimization worker
- Workspace settings persistence
- Progress state
- Result summary
- Recommended-result summary
- Formation comparison deltas
- Copy summary and copy lineup actions
- Last successful result persistence
- Recommended lineup, orders, tactic, possession, xG, and probabilities

Acceptance criteria:

- Optimization runs off the UI thread.
- Users see progress or busy status.
- Results are readable and comparable.
- The Analyze Match action requires a CSV, opponent, and at least one formation.
- Last selected CSV path, opponent, and formations are restored.
- Last successful analysis is restored from serializable view-model data.
- Any supported formation can be analyzed and restored from persisted results.
- Injured players are excluded from initial Match recommendations, Workspace
  recalculation, Bench and replacement candidates in Current Available mode.
- Full Strength Match simulation can include unavailable players and displays a warning.
- Engine calculations remain unchanged.

### Epic 7: Reports

Goal: make recommendation output reviewable and export-ready.

Deliverables:

- Reports view
- Latest match analysis report
- Formation and lineup summary sections
- Export-ready report service boundary

Acceptance criteria:

- Reports read from application state or stored results.
- Report formatting is not duplicated in views.
- No engine calculations are introduced in report code.

### Epic 8: Polish And Reliability

Goal: make the app feel coherent and trustworthy.

Deliverables:

- Consistent spacing, typography, and controls
- Empty states
- Error messages
- Confirmation dialogs
- Keyboard shortcuts for common actions
- Basic application logging

Acceptance criteria:

- Main workflows are understandable without reading docs.
- Common failure cases produce useful feedback.
- No long task freezes the UI.

### Epic 9: Tkinter Retirement Plan

Goal: decide the fate of the legacy `app.py`.

Options:

- Keep as legacy fallback.
- Move to `legacy/tkinter_app.py`.
- Remove after PySide6 parity.

Acceptance criteria:

- One primary desktop entry point is documented.
- Install/run scripts target the PySide6 app.
- Legacy behavior is not confused with Alpha 0.2.

## Post Alpha 0.2 Candidates

### Alpha 0.3: Decision Lab

Goal: explain why a recommendation is selected and what trade-offs it creates.

Deliverables:

- Deterministic reasoning layer under `ht_coach_app/reasoning`.
- Recommendation reasons, risks, tactical observations, confidence assessment, sector
  matchup interpretation, and formation comparison conclusions.
- Polished coaching language that avoids misleading best-channel labels when every
  sector is unfavorable.
- xG interpretation bands, tactic-gain wording, and clean optimization impact display.
- Decision Lab section in Match results.
- Copy-ready Decision Lab summary.
- Persisted serializable reasoning data with backward-compatible restore.

Acceptance criteria:

- Reasoning never reruns optimizers or changes engine formulas.
- Every explanation is traceable to displayed match metrics.
- Confidence describes recommendation strength relative to analyzed alternatives.
- No external AI service, LLM, network dependency, or API call is introduced.

### Alpha 0.4: Formation Viewer

- Alpha 0.4.1 Formation Viewer: read-only pitch board for match recommendations.
- Alpha 0.4.2 Player Intelligence: deterministic selected-player profile,
  why-selected explanation, tactical contributions and same-role alternatives.
- Alpha 0.4.2.1 Compact Match Workspace: responsive full-pitch scaling, collapsible
  analysis inputs and a horizontal board/inspector workspace before lineup editing.
- Alpha 0.4.3 Interactive Workspace: replace players in an editable Workspace Lineup
  while preserving the immutable optimizer recommendation and requiring explicit
  recalculation.
- Alpha 0.4.3.1 Workspace Recalculation and Match Layout Fixes: evaluate the current
  Workspace Lineup as fixed input, add evaluated Workspace state, simplify the Match
  summary, keep Analysis Setup collapsible, add page-level scrolling and correct pitch
  goal/corner geometry.
- Alpha 0.4.4 Drag and Drop: pitch-slot swaps and dragged replacement candidates with
  Apply/Cancel previews and no automatic recalculation.
- Alpha 0.4.4.1 Integrated Bench Panel: dedicated roster-minus-lineup Bench beside the
  pitch, Bench exchange previews, starter-to-Bench exchange and keyboard fallback.
- Alpha 0.4.5 One-Click Workspace: valid click and drag edits commit immediately,
  automatic fixed-lineup recalculation is debounced, stale results are ignored, Reset
  Workspace remains the only global edit action, and Player Intelligence distinguishes
  `Why Recommended` from `Workspace Impact`.
- Alpha 0.4.6 Change Analysis and Internationalization: explain the latest Workspace
  change with calculated before/after values, add English and Spanish translation
  catalogs, and persist the selected language.
- Alpha 0.4.7 Tactical Advisor: rank deterministic recommendations for what to improve
  next using evaluated match results, localized advisor copy and persisted verbosity.
- Alpha 0.4.7.1 Actionable Tactical Advisor: split Advisor output into Action,
  Observation and Warning cards, reserve impact badges for measured evaluated changes,
  centralize sector matchup mapping, and prevent unevaluated tactical context from
  appearing as actionable advice.
- Alpha 0.4.8 Match Intelligence: add a central deterministic tactical interpretation
  layer with matchup classification, team profiles, opportunities, risks, three
  tactical focuses, a narrative summary and a compact matrix.
- Alpha 0.5.5.1 Decision Lab Localization and Match Intelligence Clarity: localize
  Decision Lab presentation/copy, label recommendation support separately from match
  probabilities, and suppress direct Match Intelligence margins when rating scales are
  not comparable.
- Alpha 0.5.6 Rating Engine Alignment Audit: document the full rating pipeline,
  formalize source-scale concepts, validate Hattrick decimal imports, test quarter-step
  hypotheses, and classify current TeamRater values as not yet directly convertible to
  Hattrick decimal ratings.
- Alpha 0.5.6.1 Rating Validation Framework: add reusable fixture storage, official
  versus predicted rating separation, completeness classification, JSON loading,
  validation metrics, structured reports, a CLI validator and a future prediction
  provider interface without implementing prediction or conversion.
- Alpha 0.5.6.2 Squad Builder Assisted Lineup: unify click and drag lineup operations,
  add starter-to-starter click swaps, manual lineup state, optimized restore, assisted
  position/order recommendations and explicit apply actions without implementing the
  future constraint-based lineup optimizer.
- Alpha 0.5.6.2.1 Squad Builder Manual Intent and Automatic Orders: treat manual
  player-slot decisions as authoritative, automatically choose best supported individual
  orders for affected slots, remove visible Apply recommendation controls, orient the
  pitch like the Hattrick lineup editor and remove primary Squad Export.
- Alpha 0.5.6.2.2 Initial Lineup Automatic Orders: finalize every starter's supported
  individual order before saving the optimized Workspace snapshot, so initial load,
  reload and Restore Optimized Lineup reproduce the same complete recommendation.
- Alpha 0.5.6.2.3 Match Manual Intent and Viewport Stability: preserve manual
  player-slot assignments through Match refresh, keep order optimization scoped to the
  chosen slots, discard stale revision results and restore scroll/tab/selection state.
- Alpha 0.5.7 Midfield Rating Engine v1: only after enough complete validation fixtures
  exist, investigate a measured midfield predictor against the validation framework.
- Alpha 0.5.8 Defense Rating Engine v1: validate defensive sector prediction candidates
  against real fixtures without changing existing optimizer scoring.
- Alpha 0.5.9 Attack Rating Engine v1: validate attacking sector prediction candidates
  against real fixtures without changing existing optimizer scoring.
- Alpha 0.4.9 What-If Lab: explore controlled tactical alternatives from the evaluated
  Workspace without changing stable engine formulas.
- Match scenario history.
- Exportable reports.
- Advanced opponent scouting notes.
- Multiple roster profiles.
- SQLite persistence.
- Visual comparison charts.
- Theme customization.
- Packaging as a Windows executable.

## Risks

- UI code may grow too quickly if controllers and services are skipped.
- Long optimization tasks can make the app feel broken unless worker architecture is used.
- Duplicating engine logic in the desktop app would create inconsistent recommendations.
- JSON persistence can become limiting if scenario history grows.

## Definition Of Done For Alpha 0.2

- PySide6 app is the primary desktop experience.
- Squad, opponents, match analysis, reports, and settings are available.
- Engine calculations are unchanged except for confirmed bug fixes.
- User data persists locally.
- Long-running optimization does not block the UI.
- Documentation matches the implemented architecture.
