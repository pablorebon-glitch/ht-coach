# HT Coach Alpha 0.2 Architecture

## Product Direction

HT Coach Alpha 0.2 is a professional desktop application for planning Hattrick matches.

The optimization engine is considered stable. Alpha 0.2 must treat `engine/`, the core
domain models in `models/`, and the validated optimization pipeline as a calculation
backend. New work should focus on the desktop application, orchestration, persistence,
navigation, and user experience.

## Architectural Rule

Do not modify engine calculations unless fixing a confirmed bug.

Desktop application code may call the engine, adapt input and output data, persist user
workspaces, and present recommendations. It must not duplicate rating formulas,
optimization logic, tactic math, probability calculations, or formation scoring.

## Target Layers

```text
ht_coach_app/
  main.py
  app.py
  core/
  controllers/
  services/
  state/
  views/
  widgets/
  persistence/
  workers/

engine/
models/
importers/
database/
tests/
docs/
```

The current `app.py` can remain as a legacy Tkinter entry point during the migration.
The PySide6 application should be introduced beside it and become the primary desktop
surface once feature parity is reached.

## Layer Responsibilities

### Desktop Shell

`ht_coach_app/app.py`

- Creates the `QApplication`.
- Applies theme, fonts, and application metadata.
- Builds the main window.
- Wires high-level dependencies.
- Owns startup and shutdown behavior.

`ht_coach_app/main.py`

- Provides the executable entry point.
- Parses basic launch flags if needed later.
- Starts the desktop shell.

### Core

`ht_coach_app/core/`

Shared application infrastructure that is not tied to a specific screen.

Expected modules:

- `paths.py`: resolves workspace, config, cache, database, and import/export paths.
- `events.py`: defines application-level event names or signal contracts.
- `errors.py`: defines desktop-facing exceptions and user-safe error messages.
- `constants.py`: contains UI constants that are not business rules.

### Controllers

`ht_coach_app/controllers/`

Controllers coordinate user actions. They are the boundary between views and services.

Controllers should:

- Receive UI events from views.
- Validate user intent at interaction level.
- Call services.
- Update application state.
- Trigger navigation or notifications.

Controllers should not:

- Contain engine formulas.
- Build complex widgets.
- Persist files directly.
- Know storage formats beyond service contracts.

Initial controllers:

- `NavigationController`: switches central pages without opening new windows.
- `SquadController`: load players, refresh squad state, handle CSV import errors.
- `OpponentController`: create, update, delete, and select opponents.
- `MatchController`: run matchup optimization against selected opponent.
- `ReportsController`: prepare recommendation summaries and exports.
- `SettingsController`: manage user preferences and app-level configuration.

### Services

`ht_coach_app/services/`

Services provide application use cases. They adapt stable engine APIs to desktop
workflows.

Suggested services:

- `RosterService`
  - Loads players through `importers.csv_importer`.
  - Normalizes import errors for the UI.
  - Exposes roster summaries.

- `OpponentService`
  - Manages saved opponents.
  - Owns validation rules for opponent names and rating values.
  - Delegates storage to persistence repositories.

- `OptimizationService`
  - Calls `FormationOptimizer`, `LineupOptimizer`, and matchup optimization entry points.
  - Converts engine results into view models.
  - Does not alter engine calculations.

- `ReportService`
  - Formats recommendation summaries for display and future export.
  - Keeps report formatting out of controllers.

### Views

`ht_coach_app/views/`

Views are full application screens or major tabs. They compose widgets and expose signals
for controllers.

Initial views:

- `DashboardView`
  - Overview of loaded roster, selected opponent, and latest recommendation.

- `SquadView`
  - CSV loading, player table, roster filters, and player details.

- `OpponentsView`
  - Saved opponent list, opponent editor, ratings editor, and delete confirmation.

- `MatchView`
  - Selected opponent, optimization controls, progress, and result comparison.

- `ReportsView`
  - Saved reports, future exports, and recommendation summaries.

- `SettingsView`
  - Paths, theme preference, and future engine configuration visibility.

Views should not call engine modules directly.

### Widgets

`ht_coach_app/widgets/`

Reusable UI components with narrow responsibilities.

Suggested widgets:

- `RatingInputGrid`: seven sector ratings with validation and consistent labels.
- `PlayerTable`: roster table with sorting and selection.
- `OpponentList`: saved opponent list with empty state.
- `FormationResultTable`: sortable formation comparison.
- `MatchResultPanel`: win/draw/loss, xG, possession, tactic, and lineup summary.
- `StatusBanner`: non-blocking validation and task messages.
- `BusyOverlay` or `ProgressPanel`: long-running optimization feedback.

Widgets may expose Qt signals but should not own application workflows.

### Persistence

`ht_coach_app/persistence/`

Persistence stores user-owned application data. It should be replaceable without changing
views or controllers.

Initial persistence can be JSON files under a local application data folder:

```text
user_data/
  opponents.json
  settings.json
  recent_files.json
```

Suggested repositories:

- `OpponentRepository`
  - Reads and writes saved opponents.
  - Preserves stable JSON shape.
  - Handles migrations if fields are added later.

- `SettingsRepository`
  - Stores UI preferences and last-used paths.

- `RecentFilesRepository`
  - Tracks recent CSV imports.

Long term, SQLite may replace JSON if saved matches, scenario history, or richer search
become important.

### State

`ht_coach_app/state/`

Application state should be explicit and small. The app should avoid hidden state spread
across widgets.

Suggested state objects:

- `AppState`
  - Current roster.
  - Selected opponent.
  - Active navigation item.
  - Last optimization result.
  - Busy task metadata.

- `RosterState`
  - Loaded player list.
  - Source CSV path.
  - Import timestamp.

- `OpponentState`
  - Saved opponents.
  - Selected opponent id or name.
  - Dirty editor flag.

- `OptimizationState`
  - Current request.
  - Progress status.
  - Result or error.

State can be implemented with plain Python dataclasses plus Qt signals emitted by a
central store. The goal is predictable updates, not a large framework.

### Workers

`ht_coach_app/workers/`

Optimization can take several minutes. Long-running work must not block the UI thread.

Use Qt worker patterns:

- `QThreadPool` plus `QRunnable`, or
- dedicated `QThread` workers for cancellable tasks.

Worker responsibilities:

- Execute service calls in the background.
- Emit progress, result, and error signals.
- Never update widgets directly.

### Navigation

Alpha 0.2 should use a persistent left navigation rail with a stacked content area.

Epic 1 navigation:

1. Dashboard
2. Squad
3. Opponents
4. Match
5. Reports
6. Settings

This is more professional and scalable than a tab-only interface. Tabs may still be used
inside individual screens when they represent local detail sections.

### Dependency Direction

Allowed dependency flow:

```text
views/widgets -> controllers -> services -> engine/models/importers/persistence
controllers -> state
services -> state view models
persistence -> models or persistence DTOs
```

Disallowed dependency flow:

```text
engine -> ht_coach_app
models -> ht_coach_app
views -> engine
widgets -> persistence
persistence -> views
```

## Data Flow Example

Match analysis should flow like this:

```text
User clicks Optimize
  -> MatchAnalysisView emits optimize_requested
  -> MatchAnalysisController reads AppState
  -> OptimizationService builds engine request
  -> Background worker calls FormationOptimizer.optimize_against
  -> Service maps engine result to MatchAnalysisViewModel
  -> AppState stores latest result
  -> MatchAnalysisView renders result panels
```

The engine remains unaware of the desktop application.

## View Models

Engine objects are useful internally, but views should receive display-ready view models.

Examples:

- `PlayerRowViewModel`
- `OpponentEditorViewModel`
- `FormationResultRowViewModel`
- `MatchAnalysisResultViewModel`
- `LineupRecommendationViewModel`

View models should contain formatted values where appropriate, such as percentages,
rating strings, labels, and table rows. This avoids formatting duplication across views.

## Testing Strategy

Engine tests remain focused on calculation correctness.

Desktop tests should focus on:

- Service behavior around engine calls.
- Persistence round trips.
- Controller state transitions.
- View model formatting.
- Widget validation where practical.

Avoid brittle screenshot tests early. Prefer fast unit tests for services and state.

## Migration Strategy

1. Keep the stable engine untouched.
2. Add PySide6 application package beside existing Tkinter app.
3. Move opponent persistence into app-facing persistence/services.
4. Implement PySide6 shell and navigation.
5. Add state and service boundaries.
6. Port squad loading.
7. Port opponent manager.
8. Port match analysis with background workers.
9. Add reports and exports.
10. Retire or freeze Tkinter app once PySide6 reaches feature parity.

## Non-Goals For Alpha 0.2

- Rewriting engine calculations.
- Introducing a web server.
- Adding cloud sync.
- Adding account management.
- Replacing all persistence with a database before the data model needs it.
- Building a plugin system.
