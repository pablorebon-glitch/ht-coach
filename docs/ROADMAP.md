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

Acceptance criteria:

- Users can load `players.csv`.
- Player table supports sorting.
- Import errors do not crash the app.
- Match receives roster path changes without restarting the app.
- No engine formulas or optimizer calculations are changed.

### Epic 5: Opponent Manager

Goal: make opponent management a first-class desktop workflow.

Deliverables:

- Opponents view
- Opponent list
- Rating editor
- Save, update, duplicate, delete, and select actions
- Repository/service/controller boundaries
- Validation feedback
- JSON persistence under the application data directory

Acceptance criteria:

- Users can maintain multiple opponents.
- Empty or invalid opponent names are rejected.
- Saved opponents are available to Match Analysis.
- No new opponent workflow is added to the legacy Tkinter app.

### Epic 6: Match Analysis

Goal: port the complete opponent optimization workflow.

Deliverables:

- Match Analysis view
- Players CSV selector and loaded player count
- Opponent selector
- Formation selector generated from the full supported catalog
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
