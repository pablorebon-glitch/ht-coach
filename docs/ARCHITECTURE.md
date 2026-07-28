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

Opponent rating calibration lives under `engine/ratings` as a presentation adapter.
It labels Hattrick decimal ratings and HT Coach internal contribution ratings with
their source scale, builds canonical sector matchup rows, and only calculates a direct
advantage when both values share the same scale. It must not introduce conversion
multipliers, offsets, TeamRater changes, optimizer changes or probability changes.

Alpha 0.5.6 adds `engine/ratings/rating_alignment.py` as an audit and diagnostics layer
for rating scale identity. It formalizes internal contribution, Hattrick decimal,
quarter-step and unknown sources, validates Hattrick decimal descriptive sublevels, and
records candidate conversion behavior without adopting an internal-to-decimal
conversion. The audit classification is C: current TeamRater sector values remain
internal contribution totals and are not directly comparable with imported Hattrick
decimal ratings.

Alpha 0.5.6.1 adds `engine/rating_validation` as a Qt-independent validation framework
for future rating engines. It stores real-match fixtures, separates official Hattrick
ratings from supplied predictions, classifies fixture completeness, calculates error
metrics and returns structured reports. It does not implement prediction, conversion,
calibration, optimization or rating estimation.

Alpha 0.5.8 adds `engine/hattrick_ratings` as the first independent Hattrick-oriented
rating estimator. `engine/hattrick_ratings/midfield` predicts only own-team midfield in
Hattrick quarter-step units and remains separate from TeamRater internal contribution
totals, optimizers, Decision Lab, Match Intelligence, probabilities and expected-goals
calculations. Predictions include model version `midfield-v1`, confidence,
assumptions, warnings and a structured breakdown. The model is explicitly
uncalibrated until enough complete official match fixtures exist.

Alpha 0.5.8.1 adds `engine/hattrick_ratings/calibration` as the evidence layer for
real played matches. It freezes lineup/context snapshots, stores official Hattrick
midfield ratings, validates record quality, generates model-versioned observations and
reports aggregate/segmented error metrics. It may export/import Rating Validation
Framework fixtures, but it must not tune `midfield-v1`, convert internal contribution
totals, change optimizers, change probabilities or alter desktop workspace layout.

Alpha 0.5.8.2 adds `engine/history` as the canonical historical match foundation. It
stores durable match snapshots with explicit schema versioning, stable snapshot IDs,
match context, opponent metadata, tactical setup, authoritative lineup orders, predicted
ratings, official played-match ratings and provenance. It also owns cohort
classification, previous-equivalent snapshot selection, deterministic JSON persistence
and a small developer CLI. It does not compare ratings, generate insights, validate
decisions, tune rating engines, call optimizers or modify any analytical formula.

Alpha 0.5.6.2.1 refines `ht_coach_app/workspace` around manual intent. The initial
optimizer result remains the global recommendation, but later valid manual slot
assignments are authoritative. `WorkspaceService` is the canonical presentation-
independent boundary for starter swaps, Bench exchanges, click selection, manual state,
optimized-lineup restore and automatic affected-slot order selection. Qt widgets
translate clicks and drops into service operations; they do not duplicate lineup
business rules.

Alpha 0.5.7 adds `engine/weekly_training` as a planning layer for training exposure.
It owns training-week dates, Playmaking slot rules, persisted priorities, match records,
coverage aggregation and constrained second-match lineup planning. It reuses the
existing player analyzer, formation catalog, Formation Board mapper and automatic order
optimization, and it must not retune ratings, probabilities, tactics, orders or
optimizer formulas.

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
  history/
    evolution/
  hattrick_ratings/
    calibration/
    midfield/
  rating_validation/
  squad_evolution/
  squad_health/
  weekly_training/
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

### UI Design System

`ht_coach_app/ui/design_system/`

The design system is a lightweight PySide6 layer for presentation consistency. It owns
tokens for spacing, typography, colors and layout metrics plus shared components for
semantic badges, cards, section headers, empty states and table configuration.

The design system is presentation-only. It must not call engine code, run analysis,
change rankings or reinterpret analytical results. Views may use design-system
components to display already computed statuses, warnings and summaries.

Semantic statuses are Positive, Neutral, Warning, Critical, Unavailable and Unknown.
They are mapped consistently in `colors.py` and rendered with text-bearing
`StatusBadge` widgets so status is not conveyed by color alone.

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
- `availability_service.py`: owns the eligibility rule used by Squad Builder and Match.
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

### Squad Evolution

`engine/squad_evolution/`

Squad Evolution is a planning domain. It does not modify player ratings, TeamRater,
LineupOptimizer, FormationOptimizer, probability calculations or match formulas. It
classifies long-term roster structure using existing player attributes, existing
position-fit analyzers, Squad Builder outputs and Squad Health availability records.

Age interpretation:

- `Player.age` is interpreted as age in years.
- `Player.days` is interpreted as Hattrick age days when present.
- `total_age_days` is calculated only when both years and days are available.
- Missing or malformed age fields become `Unknown`; the app does not invent precision.

Centralized age bands:

- Development: 17-22
- Prime: 23-28
- Experienced: 29-31
- Veteran: 32-34
- Late Career: 35+

Planning horizons are Current, Short Term and Medium Term. They alter planning risk
interpretation and priority ordering; they do not fabricate future skills, exact decline,
retirement dates, market values or transfer prices.

Starter hierarchy deliberately separates:

- Full Strength Ideal XI: normal structural starter hierarchy for succession.
- Current Available Ideal XI: immediate operational coverage when availability changes.

This prevents temporary injury replacements from becoming long-term starters in the
succession map.

Squad Evolution outputs:

- Age structure by squad, full-strength XI, current-available XI and broad role.
- Succession map with starter, current available starter, backup, successor readiness,
  operational risk and structural risk.
- Dependency analysis for roles relying on one aging or hard-to-replace player.
- Development candidates and possible future-role labels without exact ceiling claims.
- Current training focus and strategic alignment against renewal gaps.
- Identity continuity based on Squad Identity contributors and succession risks.
- Ranked priority risks with deterministic tie-breaking.

Planning scores and risk levels are separate from match-performance ratings. They are
for transfer-planning context in Alpha 0.5.4, not Hattrick match prediction.
- Malformed non-empty values are classified as `UNKNOWN`; they remain eligible because
  the current import format does not provide enough information to exclude safely.
- Suspension is represented in the domain model for future support, but no suspension
  status is inferred from the current CSV.

### Transfer Planner

`engine/transfer_planner/`

Transfer Planner is a profile recommendation layer over Squad Evolution. It consumes
already computed succession, dependency, training alignment and identity-continuity
outputs, then ranks abstract player profiles by urgency, planning objective and
internal solution availability.

It deliberately does not query live Transfer Market data, name real players, estimate
exact prices, fabricate future skills or project exact performance deltas. Profile
impact is qualitative and planning-oriented.

Transfer Planner outputs:

- Plan summary with top priority, structural needs, development needs, internal
  solutions and critical dependencies.
- Transfer needs with urgency, need type, target squad role, recommended action and
  internal-solution status.
- Recommended abstract player profile with age range, primary and secondary skills,
  optional skills, specialty preference, training compatibility, formation relevance
  and identity fit.
- Alternative profiles for budget or development-path comparisons.
- No-action scenario describing current, short-term and medium-term planning risk.

`ht_coach_app/services/transfer_planner_service.py` adapts this domain to the desktop
app, normalizes user constraints, caches the last plan for repeated view refreshes and
persists the selected planning objective, budget tier, age strategy, training-fit
preference and specialty preference through the shared workspace settings repository.

`ht_coach_app/services/transfer_planner_presenter.py` is the presentation boundary for
Transfer Planner text. It converts already computed transfer needs into localized,
view-ready rows and semantic detail sections. The presenter owns label mapping, safe
fallbacks and localized list formatting; it does not call the planner, alter profile
values or change analytical behavior.

The Squad page displays Transfer Planner as a planning tab beside Ideal XI, Players and
Evolution. The view never calls Squad Evolution or optimization code directly; it
receives a view-ready result from `SquadController` through `TransferPlannerService`.

- `OpponentService`
  - Manages saved opponents.
  - Owns validation rules for opponent names and rating values.
  - Exposes the canonical Hattrick sector entry order:
    midfield, right defense, central defense, left defense, right attack, central
    attack, left attack, indirect set pieces defense and indirect set pieces attack.
  - Delegates storage to persistence repositories.

`ht_coach_app/services/opponent_ratings_clipboard_parser.py` parses plain text copied
from Hattrick rating tables. It accepts Spanish and English sector aliases, extracts
optional team/match metadata for preview, keeps decimal values authoritative, ignores
average-rating/game-plan rows and uses explicit `Indirect set pieces` context before
mapping generic Defense/Attack rows to indirect sectors.

The parser treats clipboard content as untrusted text. It does not render markup, open
links, call the network or modify analytical state. Clipboard metadata is preview-only;
opponent JSON compatibility remains unchanged.

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

- `HistoricalMatchAppService`
  - Builds and persists historical snapshots from existing `MatchAnalysisResult` view
    models through `engine.history.HistoricalSnapshotFactory`.
  - Stores snapshots under the application data directory in `historical_matches.json`.
  - Does not run Qt code, call optimizers, create comparison insights or silently
    reinterpret missing official match data.
  - Uses explicit snapshot IDs; when callers supply the same ID, repository `save`
    replaces that snapshot instead of creating uncontrolled duplicates.

### Historical Match Intelligence

`engine/history/`

The historical layer is Qt-independent and acts as the canonical long-term match record.

Modules:

- `models.py`: immutable snapshot, context, opponent, tactical setup, lineup, rating,
  prediction, official-result, cohort and provenance dataclasses with explicit
  `to_dict` and `from_dict` contracts.
- `enums.py`: stable persisted values for competition type, team type, stage, home/away,
  schedule group, selector type, rating source and snapshot source.
- `serialization.py`: deterministic UTF-8 JSON, repository payloads and atomic writes.
- `repository.py`: JSON-backed save, replace, get, list, delete, import and query
  operations.
- `query_service.py`: typed filtering by date, competition, team type, stage, opponent,
  home/away, season, cohort and rating/prediction presence. Default sorting is
  chronological ascending by match date, kickoff time, creation time and snapshot ID.
- `cohort_classifier.py`: deterministic schedule grouping for weekend competitive,
  midweek competitive, friendly/training, other and unknown contexts.
- `previous_match_selector.py`: previous-match, previous-league, previous-cup,
  previous-friendly, previous-first-team, previous-same-cohort and custom selection.
- `snapshot_factory.py`: maps existing Match analysis view models into planned
  snapshots while preserving the authoritative lineup, individual orders and order
  sides.
- `validation.py`: explicit validation for snapshot identity, schema, probability
  bounds, starter uniqueness, tactical enum values, rating values and played-match
  official-data rules.
- `cli.py`: developer commands for list, inspect, validate, export, import and previous.

Schema policy:

- Persisted snapshot schema starts at version `1`.
- Future schema versions fail with a clear compatibility error until a migration exists.
- Optional fields remain optional; missing match facts are not invented.
- Official Hattrick match ID is stored when available but is never the only identity.
- Planned snapshots can be enriched with official results while preserving snapshot ID,
  created timestamp and original predictions.

Tactical left/right convention:

- `LEFT` and `RIGHT` are stored as Hattrick tactical attacking-perspective values.
- Detailed XI, player inspector, copied lineup and historical snapshots display and
  persist those canonical values.
- The Formation Board performs visual mirroring only through
  `ht_coach_app/widgets/formation_board/orientation.py`.
- A player with field side `CENTER`, order `Towards Wing` and order side `LEFT` keeps
  those canonical values; the board uses the order-side sector for visual placement
  without mutating the player's field side.

Future extension points remaining after Alpha 0.5.8.4: prediction MAE,
recommendation accuracy and season reports belong to Alpha 0.5.8.5 and Alpha 0.6.0.
Sector deltas, formation-change detection, player added/removed events and order
changes are implemented in Alpha 0.5.8.3; deterministic insight rules, confidence
scoring, executive summaries and the causal-language guardrail are implemented in
Alpha 0.5.8.4 below. A Match History UI surfacing all three history layers
(snapshots, evolution, insights) together is scoped but not yet built — see
docs/ROADMAP.md.

### Historical Evolution Engine

`engine/history/evolution/`

Alpha 0.5.8.3 adds a second Qt-independent layer on top of `engine/history/`: given
two historical snapshots, it measures their complete evolution. It does not explain
why anything changed — that is Alpha 0.5.8.4 — and it never touches the optimizer,
rating engine, calibration, planner, snapshot schema, probability engine, midfield
engine or Formation Board.

Modules:

- `comparison_models.py`: `Trend` enum and `TrendThresholds` (unchanged/major bands,
  constructor-validated, never hardcoded into comparison logic), `classify_trend`, and
  `SectorEvolution` (previous/current value, absolute delta, percentage delta, trend).
- `comparison_metrics.py`: pure delta primitives (`absolute_delta`,
  `percentage_delta`, `safe_average`) — a percentage delta against a zero previous
  value is `None` (undefined), not infinite.
- `comparison_result.py`: the aggregate result dataclasses — `OverallEvolution`,
  `FormationEvolution`, `TacticalEvolution`, `LineupPlayerChange` /
  `LineupChangeStatus` / `LineupEvolution`, `MetricDelta` / `PredictionEvolution`, and
  the top-level `HistoricalEvolutionResult`.
- `comparison_selector.py`: a thin adapter over the existing
  `PreviousMatchSelector` / `PreviousMatchSelection` (previous match, previous league,
  previous cup, previous friendly, same cohort, custom) — selection logic itself is
  not duplicated.
- `comparison_validation.py`: `ensure_comparable` guards against comparing a snapshot
  to itself or against a missing snapshot; missing *optional* data inside a valid
  snapshot is handled field-by-field in the engine, not treated as an error.
- `comparison_engine.py`: the deterministic comparison functions
  (`compare_sectors`, `compare_overall`, `compare_formation`, `compare_tactical`,
  `compare_lineup`, `compare_prediction`, `evolution_score`), the `compare()` entry
  point, and `HistoricalEvolutionEngine`, a facade combining comparison with the
  Comparison Policies above (`compare_with_previous`, `compare_with_previous_league`,
  `compare_with_previous_cup`, `compare_with_previous_friendly`,
  `compare_same_cohort`, `compare_custom`).

Design notes:

- Lineup matching uses stable player identity — `player_id` when present, otherwise a
  normalized `player_name` — never lineup row position, so a reordered lineup with the
  same players reports no changes.
- Trend classification is threshold-based on the *percentage* delta so it behaves
  consistently across different rating scales; thresholds are a constructor argument
  (`TrendThresholds`), never a hardcoded constant inside comparison logic.
- `evolution_score` is documented, not a hidden formula: average sector percentage
  delta divided by 10, rounded to 2 decimals. It is explicitly a summary metric, not a
  rating.
- Every `compare_with_*` convenience method returns `None` (not an error) when no
  eligible previous snapshot exists among the supplied candidates.
- Evolution results are not persisted; they are always reproducible from the two
  input snapshots plus the thresholds used.

### Historical Insights Engine

`engine/history/insights/`

Alpha 0.5.8.4 adds a third Qt-independent layer, on top of `engine/history/` and
`engine/history/evolution/`: given a `HistoricalEvolutionResult`, it produces
deterministic, evidenced, confidence-scored insights and an executive summary. No
generative AI, no external API, no probabilistic language model — every insight is
either a direct rule match against structured data or nothing at all.

Modules:

- `enums.py`: `InsightCategory`, `InsightDirection`, `InsightConfidence`,
  `InsightSeverity`, `InsightRelationship` (the causal-language guardrail encoded as
  data), `EvidenceType`, `DataLimitation`.
- `evidence.py`: `InsightEvidence` — entity, previous/current value, delta, source
  snapshot, reliability, affected sectors.
- `confidence.py`: `ConfidenceInputs` and `classify_confidence`, a documented,
  deterministic decision tree (HIGH requires a direct structural change, complete
  data, a known deterministic sector effect and no contradictory evidence; MEDIUM
  requires complete-enough data and 2+ supporting signals; LOW requires at least one
  signal; anything else is INSUFFICIENT_DATA).
- `models.py`: `HistoricalInsight` (rejects evidence-less insights unless they are
  explicitly INSUFFICIENT_DATA), `ExecutiveSummary`, `InsightResult`.
- `rule.py`: `InsightContext` (current snapshot, previous snapshot, evolution
  result) and the `InsightRule` base class.
- `sector_rules.py`, `formation_rules.py`, `lineup_rules.py`, `order_rules.py`,
  `player_condition_rules.py`, `tactical_rules.py`, `prediction_rules.py`: one rule
  class per concern (never one large if/elif block). Lineup and order rules match
  players by stable identity (player ID, falling back to normalized name), reusing
  Alpha 0.5.8.3's matching approach; a `side`-change rule reads both snapshots
  directly since the Evolution Engine only tracks position/order/order-side/number.
  Player-condition rules (form/stamina/experience/skill) never claim training as a
  cause — that relationship is left to a future Training Impact Engine.
- `rule_engine.py`: `InsightRuleEngine` evaluates every rule, then deterministically
  deduplicates (each insight's `dedupe_key` defaults to its rule ID, so unrelated
  rules never collide by accident; rules that are genuinely alternative phrasings of
  the same finding opt in to a shared key) and resolves `excludes` mutual
  exclusivity, keeping the highest-priority, highest-confidence insight per key.
- `summary_engine.py`: `build_executive_summary` selects the overall direction, main
  improvement, main decline, strongest likely contributor, summary confidence and a
  missing-ratings limitation purely from already-generated insights.
- `validation.py`: `ensure_insight_context_valid` guards against a missing snapshot
  or an evolution result that doesn't match the given snapshot pair.
- `__init__.py`: `generate_insights(current, previous, evolution, comparison_target_key)`
  — the single pure-function entry point tying the above together.

Design notes:

- Domain rules never return translated strings — only stable `title_key` /
  `message_key` plus structured `message_params`, matching the existing
  localization convention (see Localization below).
- The flagship example from the sprint brief — several inner midfielders switching
  to an Offensive order alongside an improved midfield rating — is implemented
  literally as `InnerMidfieldersOffensiveContributorRule`, returning
  `InsightRelationship.LIKELY_CONTRIBUTOR` with `MEDIUM` confidence, never asserting
  causality.
- `ht_coach_app/services/historical_insights_service.py` bridges snapshot lookup,
  Alpha 0.5.8.3's comparison policies (previous match/league/cup/friendly/cohort/
  custom) and insight generation into one call; `historical_insights_formatting.py`
  groups results into the requested visual hierarchy (summary, high-priority,
  other, limitations) without generating any text itself.
- Static-import and behavioral regression tests
  (`tests/test_history_responsibility_boundaries.py`) confirm the insights (and
  evolution) packages never import or invoke `FormationOptimizer`,
  `LineupOptimizer`, `TacticOptimizer` or `OrderOptimizer`.
- Not yet built: the Match History UI itself. See docs/ROADMAP.md's Alpha 0.5.8.4
  entry for why a coherent single screen is deferred rather than shipped partially.

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

The PySide6 Match page is responsible for scale-aware presentation. If the recommended
formation carries Opponent Rating Calibration rows where HT Coach internal contribution
ratings and Hattrick decimal opponent ratings are not directly comparable, the view
does not display direct matchup margins, advantage classes or difference-based tactical
signals from Match Intelligence. It keeps within-team profile context and possession
signals, and the Opponent Rating Calibration table continues to show the raw values with
their source scales. No conversion factor is introduced.

### Rating Validation

`engine/rating_validation/`

The Rating Validation framework measures future predicted Hattrick ratings against
official Hattrick ratings from real fixtures. It is independent of Qt and independent of
the current optimizer stack.

Modules:

- `fixture.py`: fixture model, official rating model, predicted rating model,
  completeness classification and future `RatingPredictionProvider` interface.
- `dataset.py`: immutable fixture collection with filtering, grouping and duplicate
  identifier protection.
- `loader.py`: JSON fixture loading from files or directories.
- `metrics.py`: absolute error, MAE, maximum error, RMSE, mean signed error and counts.
- `validator.py`: fixture and dataset validation, skipped-comparison handling and metric
  aggregation.
- `report.py`: structured validation reports, coverage and fixture summaries.
- `exceptions.py`: loader, fixture and duplicate-data exceptions.

Rules:

- official ratings are observed Hattrick decimal values;
- predicted ratings must be supplied by fixtures or a future provider;
- missing predictions are ignored and reported;
- missing sectors reduce comparison coverage;
- no HT Coach internal contribution value is converted to a Hattrick decimal rating;
- no TeamRater, optimizer, probability, xG, Decision Lab, Match Intelligence or
  Transfer Planner behavior is changed.

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
- slots own tactical position, side and pitch coordinates; players move between slots
  without carrying the old slot's tactical assignment, then receive an automatic valid
  order for the assigned slot;
- Bench is derived from loaded roster players minus the displayed Workspace Lineup and
  is never an independent source of truth;
- valid click and drag edits commit immediately to the Workspace Lineup;
- click-to-click and drag-and-drop starter swaps share the same service operation;
- Match manual edits are slot-authoritative: evaluated refreshes preserve the current
  player-slot assignment and merge only evaluated metadata into the board;
- applying an evaluated Workspace result does not increment the manual lineup revision;
  revisions advance only for user-intent changes, and stale analysis results are
  discarded before they can repaint the pitch;
- goalkeeper slots are protected from field-player swaps;
- Restore Optimized Lineup restores the original recommendation without rerunning the
  optimizer;
- manual state uses neutral manual-adjusted language and does not imply the lineup is
  wrong;
- manual position choices are not contradicted by persistent position recommendations;
- automatic orders enumerate existing `OrderOptimizer.ALLOWED_CONFIGURATIONS`, compare
  internal contribution totals and preserve the current valid order on ties;
- Workspace creation applies the same automatic-order operation to every starter before
  persisting the original optimized snapshot, so initial load, reload and Restore
  Optimized Lineup show identical finalized orders;
- the Formation Board pitch uses normalized coordinates in Hattrick visual order:
  goalkeeper, defenders, midfielders, forwards;
- recalculation is automatic, debounced and routed back through `MatchController`;
- Workspace recalculation evaluates the current fixed lineup through application-layer
  orchestration around existing `TeamRater` and `TacticOptimizer` calculations;
- Match recalculation consumes the assigned `WorkspaceState` lineup directly, including
  player ids, slot ids, formation, individual orders and order sides. It does not rerun
  starting-XI, lineup or player-slot optimizers after a manual edit;
- stale recalculation results are discarded when the Workspace revision has changed;
- no engine formulas, probability calculations, Decision Lab rules or optimizer behavior
  are changed.

Assisted Lineup deliberately defers constraint-based lineup optimization. It does not
implement mandatory players, rest lists, training-priority players, locked positions,
minimum win probability, automatic formation changes or new optimizer scoring.

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
  -> MatchWorkspaceService applies Squad Health eligibility for Current Available mode
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
