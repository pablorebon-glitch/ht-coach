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

The Tactical Advisor lives under `engine/advisor`, but it is an expert-system layer over
already evaluated result data. It does not alter engine formulas or optimizer behavior.

Match Intelligence lives under `engine/match_intelligence`. It is a deterministic
interpretation layer over already evaluated match results. It profiles both teams,
classifies attack-versus-defense matchups, detects opportunities and risks, generates
three tactical focuses, builds a compact matrix and writes a short narrative summary
without recalculating ratings or calling optimizers.

## Target Layers

```text
ht_coach_app/
  main.py
  app.py
  core/
  controllers/
  services/
  reasoning/
  match_intelligence/
  change_analysis/
  player_intelligence/
  workspace/
  state/
  views/
  widgets/
  persistence/
  workers/

engine/
  advisor/
  squad_health/
models/
importers/
database/
tests/
docs/
```

The current `app.py` can remain as a legacy Tkinter entry point during the migration.
The PySide6 application should be introduced beside it and become the primary desktop
surface once feature parity is reached.

As of Epic 1, the PySide6 application is the primary Alpha 0.2 surface. The legacy
Tkinter `app.py` is preserved for backward compatibility only and should not receive new
features.

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
- `localization.py`: loads UI translation catalogs, returns localized strings, applies
  English fallback and parameter substitution.

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
- `SquadController`: load players, refresh squad state, handle CSV import errors,
  apply filters, build the Squad Builder Ideal XI view, export visible rows, and publish
  roster path changes.
- `OpponentController`: create, update, duplicate, delete, and select opponents.
- `MatchController`: persist match workspace inputs and run matchup optimization against
  the selected opponent through a background worker. It also attaches Change Analysis
  after Workspace recalculation by comparing the previous persisted evaluated result to
  the current evaluated result.
- `ReportsController`: prepare recommendation summaries and exports.
- `SettingsController`: manage user preferences and app-level configuration.

### Services

`ht_coach_app/services/`

Services provide application use cases. They adapt stable engine APIs to desktop
workflows.

Suggested services:

- `SquadService`
  - Loads players through `importers.csv_importer`.
  - Normalizes import errors for the UI.
  - Exposes roster summaries, sortable/filterable row view models, player details,
    position rankings through existing analyzers, and CSV export formatting.

- `SquadBuilderService`
  - Builds the Squad Ideal XI experience from loaded roster data.
  - Calls existing `FormationOptimizer.optimize`, which in turn uses `LineupOptimizer`,
    `TeamRater`, and `FormationAnalyzer.overall_score`.
  - Evaluates every formation from `models.formations` for Auto mode.
  - Maps results into serializable UI-facing formation, ranking, squad identity,
    tactical readiness, formation affinity, contributor and board view models.
  - Describes long-term squad capability only; it does not consider opponents and does
    not recommend match tactics.
  - Applies centralized squad availability filtering before optimization in Current
    Available Squad mode.
  - Compares Current Available against Full Strength using already evaluated formation
    outputs for impact analysis.
  - Does not duplicate optimizer behavior or introduce rating formulas.

### Squad Health

`engine/squad_health/`

The Squad Health domain is the authoritative source for availability and eligibility.
It does not score players or formations. It classifies imported health data and filters
candidate pools before existing optimizers run.

Modules:

- `models.py`: availability status, health summary, coverage and impact view models.
- `availability_classifier.py`: converts the imported `Lesiones` value into
  `AVAILABLE`, `INJURED`, `UNKNOWN`, and future-compatible states.
- `availability_service.py`: owns the eligibility rule used by Squad Builder.
- `availability_impact_analyzer.py`: compares Current Available and Full Strength
  evaluated outputs without recalculating ratings.
- `health_summary.py`: builds unavailable-player, affected-area and positional coverage
  summaries from existing roster and position evaluation data.

CSV interpretation:

- The importer reads the `Lesiones` column when present.
- Empty or missing injury values are treated as no injury data and safely eligible.
- Numeric zero is available.
- Any numeric value greater than zero is classified conservatively as `INJURED` and is
  not eligible for Current Available Squad.
- Malformed non-empty values are classified as `UNKNOWN`; they remain eligible because
  the current import format does not provide enough information to exclude safely.
- Suspension is represented in the domain model for future support, but no suspension
  status is inferred from the current CSV.

- `OpponentService`
  - Manages saved opponents.
  - Owns validation rules for opponent names and rating values.
  - Delegates storage to persistence repositories.

- `MatchWorkspaceService`
  - Calls `FormationOptimizer`, `LineupOptimizer`, and matchup optimization entry points.
  - Converts engine results into view models.
  - Does not alter engine calculations.
  - Exposes the centralized formation catalog from `models.formations`.
  - Preserves 3-5-2 and 4-5-1 as the default recommended selection for existing users.
  - Formats copy-ready match summaries and recommended lineup text from view models.
  - Runs Decision Lab reasoning after optimization finishes, using only serializable
    analysis view-model data and existing engine outputs.
  - Runs Match Intelligence after optimization finishes, using already evaluated team
    and opponent ratings from the recommended or current Workspace result.
  - Runs Tactical Advisor recommendations over already evaluated results and persists
    serializable recommendation view models.

### Reasoning

`ht_coach_app/reasoning/`

The reasoning layer turns match analysis view models into deterministic explanations.
It does not call widgets, mutate engine results, call optimizers, or introduce external
AI/network dependencies.

Modules:

- `models.py`: immutable serializable Decision Lab view models.
- `comparison_analyzer.py`: sector matchup and formation-comparison interpretation.
- `decision_lab.py`: rule-based recommendation reasons, risks, tactical observations,
  gain explanations, and confidence assessment.
- `explanation_formatter.py`: plain-text copy/report output helpers.

- `FormationBoardMapper`
  - Converts serializable match analysis results into immutable board view models.
  - Reuses centralized position, side and order formatting.
  - Does not call optimizers, persistence, or engine calculators.

### Change Analysis

`ht_coach_app/change_analysis/`

The Change Analysis layer compares two already evaluated match result view models. It
does not call the engine, optimizers, Decision Lab or Player Intelligence.

Modules:

- `models.py`: serializable view models for last change, position fit, team impact,
  sector changes and deterministic summary.
- `service.py`: compares previous evaluated Workspace values against current evaluated
  Workspace values, filters unchanged sectors, and classifies the change with fixed
  thresholds.

Rules:

- compare only calculated result values;
- use the last Workspace modification for incoming/outgoing player and slot context;
- show `in this slot` wording for position fit scores;
- persist only serializable view-model data;
- never alter rating, probability, xG, optimizer, Decision Lab or Player Intelligence
  formulas.

### Tactical Advisor

`engine/advisor/`

The Tactical Advisor answers "what should I improve next?" using deterministic rules
over the current evaluated match context.

Modules:

- `matchups.py`: centralized sector matchup mapping for own attack versus opponent
  defense and opponent attack versus own defense.
- `recommendation.py`: immutable recommendation payload with title/explanation keys,
  category, card type, confidence, impact score, estimated win delta and evaluated
  sector deltas.
- `recommendation_types.py`: category, card type and confidence enums.
- `recommendation_rule.py`: independent rule interface.
- `recommendation_engine.py`: context wrapper and initial expert-system rules.
- `recommendation_ranker.py`: duplicate removal and ranking by actionable value, then
  warnings and observations.

Initial rules:

- Lineup: uses the latest Change Analysis to recommend keeping a beneficial Workspace
  replacement, reverting a harmful one, or marking a neutral change as observation.
- Formation: recommends another evaluated formation only when the before/after result
  has a measurable win-probability improvement.
- Strength: highlights the strongest calculated sector as an observation.
- Weakness: highlights the sector most exposed against opponent ratings.
- Attack matchup: identifies efficient or inefficient attacking routes by comparing
  each own attack against the correct opposing defensive sector.
- Balance: detects low possession and whether concentrated attack targets the
  opponent's weakest defensive sector.

Rules use existing calculated values only. They do not call `TeamRater`,
`LineupOptimizer`, `FormationOptimizer`, probability, xG, Decision Lab or Player
Intelligence formulas.

When Match Intelligence is present, Tactical Advisor consumes its matchup view models
instead of reinterpreting attack-versus-defense sectors locally. Advisor ranking,
thresholds and action requirements remain separate.

### Match Intelligence

`engine/match_intelligence/`

Match Intelligence answers where the match is strong, weak, exposed and likely to be
decided.

Modules:

- `models.py`: serializable tactical intelligence view models.
- `matchup.py`: canonical own-attack and opponent-attack sector mapping.
- `matchup_analyzer.py`: matchup differences and classification as Excellent,
  Favorable, Balanced, Unfavorable or Critical.
- `strengths.py`: team and opponent profile extraction.
- `summary.py`: opportunity detection and deterministic narrative summary.
- `risks.py`: opponent route, defensive and midfield risk detection.
- `focus_analyzer.py`: exactly three concise tactical focus items.
- `intelligence_engine.py`: orchestrates all analyzers.

The module consumes already evaluated `MatchAnalysisResult` data. It does not modify
TeamRater, LineupOptimizer, TacticOptimizer, probabilities, xG, ratings or Decision Lab.

Advisor card types are intentionally strict:

- `ACTION`: a concrete evaluated formation or Workspace lineup change with before/after
  state and measured win-probability impact.
- `WARNING`: risk or unfavorable matchup context without an evaluated fix.
- `OBSERVATION`: strengths, weaknesses, efficient routes or neutral changes that help
  the coach reason without pretending to be measured improvements.

Impact badges are shown only for actions. High impact starts at `+1.5 pp` win
probability, medium at `+0.5 pp`, and low above the minimum actionable threshold.
Confidence remains independent from impact size.

### Workspace

`ht_coach_app/workspace/`

The workspace layer owns editable lineup state for the Formation Board. It is
UI-independent and does not import Qt.

Modules:

- `workspace_models.py`: workspace state, derived Bench player view models,
  replacement/swap previews, replacement candidates, revision tracking and modification
  history view models.
- `workspace_service.py`: creates editable board copies, ranks compatible replacements
  with existing player analyzers, derives Bench from roster minus Workspace lineup,
  commits immediate Bench exchanges and slot swaps, resets state, reconciles evaluated
  fixed-lineup results and prepares undo/redo history shape.

Workspace rules:

- the original recommendation is immutable;
- slots own tactical position, side, order and pitch coordinates; players move between
  slots without carrying the old slot's tactical assignment;
- Bench is derived from loaded roster players minus the displayed Workspace Lineup and
  is never an independent source of truth;
- valid click and drag edits commit immediately to the Workspace Lineup;
- reset restores the original recommendation;
- recalculation is automatic, debounced and routed back through `MatchController`;
- Workspace recalculation evaluates the current fixed lineup through application-layer
  orchestration around existing `TeamRater` and `TacticOptimizer` calculations;
- stale recalculation results are discarded when the Workspace revision has changed;
- no engine formulas, probability calculations, Decision Lab rules or optimizer behavior
  are changed.

### Player Intelligence

`ht_coach_app/player_intelligence/`

The Player Intelligence layer turns a selected Formation Board player plus loaded roster
data into deterministic explanation view models. It is UI-independent and does not
import Qt.

Modules:

- `models.py`: immutable serializable Player Intelligence view models.
- `profile_classifier.py`: deterministic, modest player-profile labels.
- `explanation_rules.py`: strengths, limitations and why-selected rules.
- `alternative_analyzer.py`: same-role candidate ranking and effective-tie wording.
- `contribution_formatter.py`: tactical contribution bars from existing contribution
  calculations.
- `service.py`: orchestrates profile, ranking, contribution and technical details.

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
  - CSV loading, player table, roster filters, position ranking, export, and player
    details.

- `OpponentsView`
  - Saved opponent list, opponent editor, duplicate action, ratings editor, and delete
    confirmation.

- `MatchView`
  - Players CSV selector, saved opponent selector, formation selection, progress, result
    comparison, and recommended XI.

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
- `PlayerDetailPanel`: complete player skills, best position, and ranking by supported
  position.
- `OpponentList`: saved opponent list with empty state.
- `FormationResultTable`: sortable formation comparison.
- `MatchResultPanel`: win/draw/loss, xG, possession, tactic, and lineup summary.
- `FormationBoard`: read-only football pitch visualization for analyzed lineups.
- `PitchWidget`: custom PySide6-painted vertical pitch.
- `PlayerCard`: compact selectable card for a recommended XI player.
- `PlayerInspectorPanel`: read-only selected-player detail surface.
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
  app_settings.json
  settings.json
  recent_files.json
```

Suggested repositories:

- `OpponentRepository`
  - Reads and writes saved opponents.
  - Preserves stable JSON shape.
  - Handles migrations if fields are added later.
  - Stores data under the application data directory.

- `SettingsRepository`
  - Stores UI preferences and last-used paths.

- `AppSettingsRepository`
  - Stores app-level preferences such as selected language and Advisor verbosity.
  - Falls back to English for missing or unsupported values.

- `MatchWorkspaceRepository`
  - Stores the last selected players CSV path, opponent, and formations.
  - Stores the last successful analysis result as serializable view-model JSON.
  - Persists Change Analysis view-model data when present.
  - Persists Tactical Advisor recommendation view-model data when present.
  - Restores results for any supported formation from the centralized catalog.
  - Uses JSON under the application data directory.
  - Keeps workspace persistence separate from widgets and engine code.

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
controllers -> state / application events
services -> state view models
services -> reasoning -> existing analysis view models
services -> engine/advisor -> existing evaluated analysis view models
widgets -> player_intelligence -> existing roster data / player analyzers
widgets -> workspace -> existing roster data / player analyzers
views/widgets -> localization -> resources/i18n
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

Roster synchronization flows through application-level events:

```text
SquadController loads roster
  -> MatchWorkspaceRepository saves players CSV path
  -> AppEvents.roster_changed emits path and player count
  -> MatchController updates MatchPage path and loaded-player count
```

## Data Flow Example

Match analysis should flow like this:

```text
User clicks Analyze Match
  -> MatchPage emits analyze_requested
  -> MatchController validates selected CSV, opponent, and formations
  -> MatchAnalysisWorker runs MatchWorkspaceService off the UI thread
  -> MatchWorkspaceService loads players with importers.csv_importer
  -> MatchWorkspaceService calls FormationOptimizer.optimize_against
  -> Service maps engine result to serializable MatchAnalysisResult view models
  -> Decision Lab creates deterministic explanations from those view models
  -> Match Intelligence creates tactical profiles, matchup classifications,
     opportunities, risks, three focuses, a summary and a matrix
  -> MatchWorkspaceRepository persists the last successful result
  -> MatchPage renders Decision Lab, recommended summary, Formation Board,
     comparison table and detailed XI
  -> FormationBoard creates an editable Workspace Lineup copy for one-click
     replacements without changing the persisted recommendation
  -> Valid Workspace edits emit workspace-modified intent
  -> MatchController debounces fixed-lineup recalculation and preserves committed
     player assignments in the refreshed board
  -> ChangeAnalysisService compares previous and current evaluated Workspace results
  -> MatchPage renders Change Analysis above the local result tabs
  -> RecommendationEngine ranks Tactical Advisor recommendations
  -> MatchPage renders Match Intelligence and Tactical Advisor as informational panels
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
- `FormationBoardViewModel`
- `FormationSlotViewModel`
- `PlayerCardViewModel`
- `PlayerInspectorViewModel`
- `PlayerIntelligenceViewModel`
- `PlayerAlternativeViewModel`
- `PlayerContributionViewModel`
- `DecisionLabResult`
- `Recommendation`
- `FormationComparison`
- `SectorComparison`

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
7. Port opponent manager to PySide6.
8. Port match analysis with background workers. The first usable Match Workspace now
   supports players CSV selection, saved opponents, full formation catalog analysis,
   progress feedback, comparison cards, recommended XI rendering, copy actions, and
   last-result restore.
9. Add reports and exports.
10. Retire or freeze Tkinter app once PySide6 reaches feature parity.

## Non-Goals For Alpha 0.2

- Rewriting engine calculations.
- Introducing a web server.
- Adding cloud sync.
- Adding account management.
- Replacing all persistence with a database before the data model needs it.
- Building a plugin system.
