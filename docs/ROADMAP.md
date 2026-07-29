# HT Coach Alpha Roadmap

## Current Position

HT Coach has a stable optimization engine and an early desktop surface. Alpha 0.2 starts
the transition from a functional prototype to a professional PySide6 desktop
application.

The roadmap protects the engine and moves product work into the application layer.

## Guiding Principles

- Preserve engine behavior unless a confirmed bug is found.
- Keep internal optimizer strength separate from predicted Hattrick rating estimates.
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

### Alpha 0.5.8: Hattrick Midfield Rating Engine v1

Goal: introduce the first independent Hattrick-oriented own-team rating estimator
without changing optimizer behavior.

Deliverables:

- `engine/hattrick_ratings` package.
- Midfield-only prediction calculator.
- Quarter-step Hattrick rating representation.
- Form, stamina and team-context support points.
- Structured breakdowns and confidence warnings.
- Rating Validation Framework provider integration.
- Synthetic reference midfield fixtures.
- Non-destructive validation CLI.

Acceptance criteria:

- Predictions are Hattrick rating estimates, not converted internal contribution totals.
- Model version `midfield-v1` is included in every prediction.
- Validation metrics use Hattrick rating units.
- No optimizer, probability, expected-goals, Squad, Planner or Match layout behavior is
  changed.

### Alpha 0.5.8.1: Real Match Calibration Dataset

Goal: create the evidence workflow needed to evaluate `midfield-v1` against played
Hattrick matches without tuning the model.

Deliverables:

- Real-match calibration record model.
- Frozen lineup and context snapshots.
- Official midfield rating input parser.
- Record validation and data quality classification.
- Model-versioned observations.
- Aggregate and segmented metrics.
- JSON repository.
- CLI workflow for add, validate, finalize, recalculate, report, export and import.
- Synthetic schema fixture and documentation.

Acceptance criteria:

- Future matches cannot be finalized.
- Official midfield ratings must be exact Hattrick quarter steps.
- Metrics are calculated in Hattrick rating units.
- Exported records integrate with the Rating Validation Framework.
- `midfield-v1` parameters, optimizers, probabilities and desktop workspace layout are
  unchanged.

### Alpha 0.5.8.2: Historical Match Intelligence Foundation

Goal: create the canonical club-history data foundation without implementing comparison,
insight or validation engines ahead of schedule.

Deliverables:

- `engine/history` package with typed historical match snapshots.
- Explicit schema version `1` and schema-aware loading.
- Snapshot identity independent from opponent name, date or official match ID.
- Match context, opponent metadata, tactical setup, canonical lineup, predictions,
  official result data, prediction-error extension point and provenance.
- Deterministic cohort classification.
- Previous-equivalent match selector for future comparison work.
- JSON repository with deterministic serialization, atomic writes and typed queries.
- Developer CLI for listing, inspecting, validating, importing, exporting and selecting
  previous snapshots.
- Small application service capable of creating snapshots from existing Match analysis
  results without rerunning optimizers.
- Centralized Formation Board tactical-left/right visual mirroring.

Acceptance criteria:

- Planned and played snapshots load safely.
- Predicted ratings and official ratings remain separate.
- Complete lineup orders and order sides are preserved.
- Snapshot creation never reoptimizes the authoritative Match Workspace lineup.
- Formation Board and Detailed XI share the same Hattrick tactical left/right semantics.
- No optimizer formulas, rating formulas, probabilities, expected-goals calculations,
  Weekly Planner behavior or layout-stabilization logic are changed.

### Alpha 0.5.8.3: Historical Match Comparison Engine

Goal: measure the complete evolution between two historical snapshots with pure
deterministic comparison — no explanation, no heuristics, no AI. Explanation is
deferred to Alpha 0.5.8.4.

Deliverables:

- `engine/history/evolution` package, Qt-independent, built entirely on the existing
  `engine/history` foundation (snapshots, cohort classification, previous-match
  selector) without modifying it.
- Sector evolution for midfield and the six directional defense/attack sectors, each
  with previous value, current value, absolute delta, percentage delta and a
  configurable-threshold trend (`major_improvement` / `improvement` / `unchanged` /
  `decline` / `major_decline`).
- Overall evolution: summed sector delta, average sector delta, best-improved and
  worst sectors, improved/declined/unchanged sector counts and an overall trend.
- Formation evolution (changed/unchanged, old/new formation).
- Tactical evolution (tactic, tactic level, attitude, confidence deltas).
- Lineup evolution matched by stable player identity (player ID first, normalized
  player name fallback) — never by row position — reporting players added, removed,
  kept, and per-kept-player position/order/order-side/shirt-number changes.
- Prediction evolution for expected goals, opponent expected goals, win/draw/loss
  probability and possession.
- A single deterministic `evolution_score` summary metric (average sector percentage
  delta scaled by 10), documented as a summary, not a rating.
- `HistoricalEvolutionEngine` service exposing `compare()`,
  `compare_with_previous()`, `compare_with_previous_league()`,
  `compare_with_previous_cup()`, `compare_with_previous_friendly()`,
  `compare_same_cohort()` and `compare_custom()`, reusing the existing
  `PreviousMatchSelector` comparison policies rather than re-implementing selection.

Acceptance criteria:

- Any two historical snapshots can be compared.
- Every sector produces a deterministic delta and trend.
- Lineup, tactical, formation and prediction evolution are all detected.
- Missing optional data (ratings, tactic level, predictions) degrades gracefully to
  `None` deltas instead of raising.
- No optimizer, rating engine, calibration, planner, snapshot schema, probability
  engine, midfield engine or Formation Board code is changed.
- `engine/history/evolution` test suite: 100% statement coverage.

### Alpha 0.5.8.4: Historical Insights Engine and Match History

Goal: turn Alpha 0.5.8.3's evolution results into deterministic, evidenced,
confidence-scored insights and an executive summary, using explicit rules only — no
generative AI, no external API, no probabilistic language model.

Deliverables:

- `engine/history/insights` package, Qt-independent, built on top of
  `engine/history` and `engine/history/evolution` without modifying either.
- A deterministic rule engine (`InsightRuleEngine`) evaluating a catalog of small,
  single-responsibility rules (sector, formation, lineup, individual-order,
  player-condition, tactical and prediction rules), each producing zero or more
  structured `HistoricalInsight` objects with stable message keys/params rather than
  translated strings.
- An evidence model (`InsightEvidence`) — every explanatory insight carries at least
  one evidence item; an insight with no evidence can only be `INSUFFICIENT_DATA`,
  enforced by the model itself, not by convention.
- A documented, deterministic confidence policy (`classify_confidence`): HIGH
  requires a direct structural change, complete data, a known deterministic sector
  effect and no contradictory evidence; MEDIUM requires complete-enough data and at
  least two supporting signals; LOW requires at least one signal; anything else is
  INSUFFICIENT_DATA.
- A causal-language guardrail encoded as data (`InsightRelationship`: observed,
  associated with, likely contributor, possible contributor, insufficient evidence)
  instead of hand-written cautious wording — e.g. several inner midfielders switching
  to an Offensive order alongside an improved midfield rating is reported as a
  `LIKELY_CONTRIBUTOR`, never as a proven cause.
- Deterministic deduplication and prioritization (`InsightRuleEngine`): each insight
  declares its own `dedupe_key` (defaulting to its rule ID, so distinct rules never
  collide by accident) and optional `excludes` for genuine mutual exclusivity; only
  the highest-priority, highest-confidence insight per key survives.
- A `SummaryEngine` (`build_executive_summary`) producing a structured
  `ExecutiveSummary` (comparison target, overall direction, main improvement, main
  decline, strongest likely contributor, confidence, limitation) purely by selecting
  among already-generated insights — never generating free-form paragraphs.
- `ht_coach_app/services/historical_insights_service.py` /
  `historical_insights_formatting.py`: an app-facing bridge combining snapshot
  lookup, Alpha 0.5.8.3's comparison policies and insight generation, plus
  presentation-only formatting (visual hierarchy grouping, evidence rows) with no
  text generation beyond fixed labels.

Match History UI: **not built in this sprint.** The app has no Match History screen
at all yet — Alpha 0.5.8.2 built the snapshot foundation and Alpha 0.5.8.3/0.5.8.4
built the comparison and insight engines, but none of the three has ever been
rendered. Building one coherent Match History page (snapshot list, details,
comparison selector, evolution panel, insights panel, data-quality limitations) is
sized like its own sprint and is intentionally deferred rather than shipped as a
partial or unstable screen. The two app services above exist specifically so that
future UI work is "wire it up," not "build the logic too."

Acceptance criteria:

- Historical Evolution results convert into structured, evidenced insights.
- Confidence is deterministic, documented and tested (including contradictory
  evidence and insufficient-data cases).
- No unsupported causal claims are generated; the flagship example (offensive inner
  midfielders alongside a midfield improvement) is reported as a likely contributor,
  never as a cause.
- Duplicate/near-duplicate insights are consolidated deterministically.
- Executive summaries are structured (keys and parameters), not free text.
- Historical insight generation never invokes `FormationOptimizer`,
  `LineupOptimizer`, `TacticOptimizer` or `OrderOptimizer` (enforced by a static
  import-scan test plus a behavioral test).
- No optimizer, rating engine, calibration, planner, snapshot schema, probability
  engine, midfield engine, Formation Board or Alpha 0.5.8.3 evolution calculation is
  changed.
- `engine/history/insights` test suite: >95% statement coverage.
- The two pre-existing date-sensitive Weekly Planner test failures are investigated,
  confirmed still preexisting and left unchanged, per the sprint's explicit
  instruction not to broaden into a Planner redesign.

### Alpha 0.5.8.5: Complete Training System

**Status: partially complete.** This sprint generalizes the previously
Playmaking-only weekly training system to all 12 senior Hattrick training types.
Given the size of the full brief (canonical catalog, weekly aggregation, Match
optimizer trade-off modes, Planner UI, full localization, persistence migration),
this entry documents what shipped in the first pass versus what remains.

Shipped:

- A fully declarative training catalog (`engine/weekly_training/training_types.py`,
  `training_effects.py`, `training_definition.py`, `training_catalog.py`) covering
  all 12 senior training types (General, Set Pieces, Defending, Scoring, Winger,
  Shooting, Short Passes, Playmaking, Goalkeeping, Through Passes, Defensive
  Positions, Wing Attacks) against the exact position/effect matrix in the brief,
  including multi-skill training (Shooting trains both Scoring and Set Pieces at
  different effect levels) and team-wide "every participant" effects (General's
  form training, Set Pieces' base training) — no `if training_type == ...`
  branching anywhere in the catalog.
- `CatalogTrainingRules`, a generalized rule provider implementing the existing
  `TrainingRuleProvider` interface (`factor_for_position`, `exposure_for_entry`,
  `capacity_for_formation`) so it works with every existing caller (Match's Cup
  optimizer, weekly coverage) without those callers changing, plus new
  multi-skill-aware methods (`factors_for_position`, `trained_skills`,
  `effect_for_position`, `trainable_positions`).
- `rule_provider_for()` now resolves all 12 types. **Playmaking is deliberately
  left dispatching to the original, untouched `PlaymakingTrainingRules` class**,
  not the catalog-driven one — see "Playmaking backward compatibility" below.
- Both previously-reported date-sensitive Weekly Planner test failures are fixed
  and root-caused, not just silenced (see "Known Test Health" below).
- 39 new tests for the catalog and generalized rule provider, both at 100%
  coverage; full existing suite re-verified at 1073 passed / 0 failed (excluding
  the separately-tracked slow optimizer test and the pre-existing tactical
  adaptation hang, both unrelated to this sprint).
- English and Spanish localization for all 12 training-type labels, the four
  effect levels (using the brief's exact Spanish wording — Completo / Reducido /
  Muy reducido / No entrena, pinned by a dedicated test so it can't silently
  drift), trained-skill names, and structured explanation templates (full/
  reduced/very-small/no-effect, participation-only, multi-skill, priority-
  retained-after-type-change, missing-set-pieces-taker).
- Persistence migration tests confirming (against the real, unmodified
  persistence code, not a mock): legacy data with no training type defaults to
  Playmaking; an explicitly saved type is never overwritten; an unrecognized
  future training type loads without crashing and degrades safely (`rule_provider_for`
  and `active_training_rules()` both return `None`); all 12 types round-trip
  through save/load; unrelated priorities/match records survive alongside an
  unknown training type (no silent data deletion); serialization is
  deterministic.
- `docs/PRODUCT_VISION.md` updated with the ten product principles from this
  sprint's brief, plus an explicit note that Club DNA remains unconfigurable
  before Alpha 0.6.0.

Deliberately not shipped in this pass (tracked as follow-up work under this same
sprint number, not pushed to 0.5.9.0):

- The Match optimizer's typed `TrainingContext` and sporting-vs-training trade-off
  modes (`SPORTING_ONLY` / `BALANCED` / `PRIORITIZE_TRAINING` /
  `REQUIRE_SELECTED_PRIORITIES`) — the Copa/Amistoso optimizer still only
  understands Playmaking's IM/Winger split; generalizing it to lock the correct
  positions for all 12 types safely (without risking the live Cup-analysis
  behavior already in production use) needs its own dedicated pass.
- The structured `PlayerTrainingResult` weekly-aggregation model and multi-skill
  coverage tracking (Shooting's Scoring and Set Pieces coverage are only tracked
  as a single combined number today, scoped to the primary skill).
- The Weekly Planner training-type selector UI and its immediate-recalculation
  wiring.

Playmaking backward compatibility: building the catalog against this sprint's own
matrix surfaced a genuine, documented discrepancy — the matrix's Playmaking rule
adds a "very small" effect for every non-IM/non-winger participant, but the
original implementation (still what real users' saved coverage numbers reflect)
always treated those positions as exactly zero. Per this sprint's own instruction
("preserve existing behavior unless it contradicts the canonical model"), this is
a genuine contradiction, so it is surfaced rather than silently applied:
`rule_provider_for("PLAYMAKING")` keeps returning the original class untouched,
and the discrepancy is captured in
`tests/test_catalog_training_rules.py::test_playmaking_very_small_tier_is_a_documented_new_behavior_not_yet_active`.
Adopting the very-small tier for Playmaking, if wanted, is a one-line dispatch
change once made deliberately rather than as a side effect of this refactor.

Known Test Health: both previously-reported failures were root-caused, not
config-tweaked away.
`test_training_week_handles_year_boundary_and_timezone_aware_datetime` failed only
because the test environment's `tzdata` package was missing — not a code bug;
fixed by adding `tzdata` to `requirements.txt`.
`test_priorities_persist_duplicate_names_and_rollover_resets_records` implicitly
built its "current week" from the real system clock via `repository.load()`, then
asserted a rollover against a hardcoded `date(2026, 7, 23)` that only made sense
while real wall-clock time happened to fall in a specific window; fixed by
injecting an explicit reference date for the initial active week, with the root
cause documented inline in the test itself.

### Alpha 0.5.9.0: Official Hattrick Rating Workflow

Goal: connect HT Coach with Hattrick's own "Copy Ratings" export so official
ratings — not just HT Coach's own predictions — become part of History. Product
principle: "HT Coach proposes. Hattrick calculates. HT Coach learns." Imported
official ratings are never regenerated or reinterpreted; they're stored exactly as
parsed.

Deliverables:

- `engine/history/official_ratings/` (Qt-independent, built on `engine/history/`
  without modifying its evolution or insights calculations): `OfficialRatingSnapshot`
  / `RatedAttribute` models, a tolerant English/Spanish `parse_official_ratings`
  parser (unknown lines are preserved, never fail parsing), validation for
  malformed/incomplete input, a deterministic three-way `compare_official_ratings`
  (prediction vs. official PRE vs. official POST, whichever are present) and a
  diagnostic (not primary-UI) `summarize_official_rating_comparison`.
- `HistoricalMatchSnapshot` gained two new optional fields, `official_pre` and
  `official_post`, coexisting with the existing `predictions` and `official_result`
  — none replaces another. Purely additive: no schema version bump, and a snapshot
  saved before this sprint loads unchanged (see
  `tests/test_official_rating_snapshot_migration.py`).
- `ht_coach_app/services/official_rating_service.py`'s `OfficialRatingImportService`:
  the "paste Copy Ratings text, attach it to a match" workflow, reusing the existing
  `HistoricalMatchRepository` rather than introducing a second storage format.
- `ht_coach_app/services/official_rating_formatting.py`'s `format_hattrick_notation`:
  a pure formatter producing the exact Hattrick-style summary text (three-number
  sector bands, "quality word (number)" formation/tactic notation) — not yet wired
  into the Match page UI (see "Not shipped" below).
- 57 new tests across parser, validation, comparison, summary, the import service,
  formatting, and snapshot migration (including a dedicated verbatim real-sample
  regression group) — 97% coverage on the new modules. Full suite re-verified at
  1143 passed / 0 failed.
- `docs/OFFICIAL_RATING_WORKFLOW.md` added, documenting the workflow, data model,
  parser tolerance rules and the "never regenerate an import" principle.

Not shipped in this pass:

- Actual Match page UI wiring for `format_hattrick_notation` (a visible summary
  section showing it) — the guardrail against redesigning the Match UI made this
  premature to wire up.
- Any UI for pasting Copy Ratings text and picking PRE vs. POST — the import
  service exists and is tested; there is no dialog or button calling it yet.
- Automatically matching an imported snapshot to the right historical match via
  the `hattrick_match_id` now extracted from the header line — the field is
  captured and tested, but nothing consumes it yet to skip manual snapshot
  selection.

**Parser calibration:** initially built from documented knowledge of the Copy
Ratings feature and marked as unvalidated; since then, calibrated against a real
paste from a live Hattrick account. The actual format turned out to be BBCode (a
`[table]` block for Defense/Midfield/Attack, `[b]Label[/b]: value` lines for
everything else, a `[matchid=...]` header), not the plain-line format originally
assumed — the parser was rewritten around the real structure, with the original
line-based approach kept only as a fallback for sectors not found in a table. The
real sample also revealed that Hattrick's actual tactic-name wording ("atacar por
el centro") differs from this app's own existing translation ("ataque por el
centro") — both are now recognized. See
`tests/test_official_ratings.py::test_real_sample_*` for the verbatim regression
tests and docs/OFFICIAL_RATING_WORKFLOW.md for the full calibration writeup.

### UX-02: Expose Complete Training and Official Match Import Workflows

Goal: two engine capabilities built in prior sprints (all 12 training types, and the
official Hattrick rating import pipeline) were complete but not user-facing. This
sprint is integration-only — no new engine logic, no new analytical formulas, no
application redesign — it exposes what already existed through small, coherent UI
additions.

**Part A — Complete Training Selector.** The Weekly Training Planner's training-type
combo (both the visible v2 tab and the hidden legacy tab kept alive for
compatibility) now populates from `TrainingType` directly — all 12 canonical types,
localized labels, canonical values as item data, never a second hardcoded list.
Changing the selection persists immediately and recalculates coverage, priorities
and warnings on the next render, since those were always derived fresh from
`state.active_training_type` rather than cached.

Building this surfaced a real bug: naively recomputing the active week when
switching training type would have silently orphaned any first/second match already
recorded that week, since `TrainingWeek.week_id` embeds the training type
(`"2026-07-26:PLAYMAKING"`) and match records are looked up by a `week_id`-scoped
prefix. `WeeklyTrainingAppService.set_active_training_type()` fixes this by keeping
the week's identity unchanged and only updating its `active_training_type` field —
see `tests/test_training_type_selector_ui.py::test_changing_training_type_does_not_orphan_recorded_matches`.

**Part B — Official Match Summary Import.** A single "Import Official Match
Summary" action was added to Match: open, paste, confirm — no wizard, no setup
pages. Three pieces of new logic support it:

- A canonical tactic-alias catalog (`engine/history/official_ratings/tactic_catalog.py`),
  reused by the parser rather than duplicated, resolving both this app's own
  historical translations and Hattrick's actual in-game wording (confirmed to
  differ) to the same canonical `Tactic` enum. Unrecognized tactics preserve their
  raw text and produce a structured warning without invalidating the rest of the
  import.
- Automatic Match ID linking (`OfficialRatingImportService.import_and_link`): one
  matching snapshot links automatically; none creates a new, identifiable one;
  more than one raises a conflict rather than guessing.
- Explicit PRE/POST replace-confirmation: importing into an already-filled slot
  requires confirmation, and a second paste is never silently reclassified as POST
  just because PRE exists. Post-match ("Copy Ratings" after a match) support is
  not claimed beyond the data model until a real post-match sample is validated,
  the same way the PRE sample was in Alpha 0.5.9.0.

A prediction-vs-official comparison is available but deliberately shows no numeric
delta — HT Coach's own predicted-rating scale isn't yet confirmed to align with
Hattrick's official scale, so a "difference" number would imply an unverified
equivalence. See docs/OFFICIAL_RATING_WORKFLOW.md for the full write-up of both
parts.

Testing: 111 new tests (selector UI, tactic catalog, match-ID linking, import UI,
prediction-comparison scale limitation, sector-order/orientation-independence)
across `tests/test_training_type_selector_ui.py`, `tests/test_tactic_catalog.py`,
`tests/test_official_rating_match_linking.py`, `tests/test_official_import_ui.py`
and additions to `tests/test_official_ratings.py` /
`tests/test_official_rating_app_service.py`. Full suite re-verified at 1198 passed
/ 0 failed (excluding the separately-tracked slow optimizer test and the
pre-existing tactical adaptation hang, both unrelated to this sprint). No rating,
probability, optimizer, calibration, or Formation Board orientation formula was
touched — the training-type selector and official import both only read/write
state that already existed.

### Alpha 0.5.9.1: Squad Intelligence

Goal: turn Squad from a roster-data screen into a player-management intelligence
screen. For any current-roster player, produce a deterministic, explainable
classification (recommended role, management status, why, training fit,
strengths/risks, next milestone) understandable in five seconds, with no raw
"Overall: 87" score exposed anywhere.

Deliverables:

- `engine/squad_intelligence/` (Qt- and localization-independent, 15 modules): a
  role catalog (11 roles) and management-status catalog (8 statuses, deliberately
  no unconditional "sell"), five qualitative dimensions (current performance,
  training potential, training fit, salary efficiency, strategic value) each with
  evidence, a documented internal-scoring layer (normalized [0,1], never shown
  directly), one-rule-per-role/status classes (never a monolithic if/elif chain)
  with a guaranteed fallback so every player gets exactly one role and one status,
  deterministic milestone selection, and a documented confidence policy.
- Reuses rather than duplicates: current performance is built from the existing
  `PlayerAnalyzer` positional ranking (no second rating engine); training fit
  reads the canonical Complete Training System via `rule_provider_for` (no second
  training matrix).
- `ht_coach_app/services/squad_intelligence_service.py`'s
  `SquadIntelligenceAppService` bridges the current roster into the engine's
  context objects. Building it against a real CSV surfaced a real bug —
  `PlayerAnalyzer.best_position()` returns a `(position, score)` tuple, not a bare
  enum — fixed and covered by a regression test using a realistic roster size.
- `ht_coach_app/services/squad_intelligence_formatting.py`: stable
  enum-to-localization-key mapping; full English/Spanish translations (151 keys)
  for every role, status, dimension value, strength, risk, milestone, confidence
  level, limitation and primary-reason template — verified by a dedicated test
  that every enum member resolves in both languages.
- UI: no new navigation page. The existing Squad "Jugadores" tab's player
  selection now also renders a compact Squad Intelligence panel (role, status,
  reason, the five dimensions, strengths, risks, next milestone, evidence,
  limitations) directly below the existing player detail. Changing the active
  training type recalculates the currently-shown report immediately.
- 122 new tests (engine, app service, localization, UI), 96% coverage on the new
  engine package. Full suite re-verified at 1320 passed / 0 failed.
- `docs/SQUAD_INTELLIGENCE.md` added, documenting the role/status catalogs, the
  documented KEY_STARTER-vs-PRIMARY_TRAINEE conflict resolution, the
  salary-efficiency and strategic-value models, and the Club Advisor extension
  point.

Not shipped in this pass:

- Historical-appearance evidence (recent starting frequency, no-show patterns) —
  the engine is built to accept it when available and degrade safely without it,
  but no adapter from `engine/history` was wired up this sprint.
- A role/status/training-fit badge or column in the main Squad table/list (the
  brief allows this but doesn't require it); the detailed panel is the
  authoritative surface for now.
- Any Club Advisor aggregation across the whole squad's reports — explicitly out
  of scope until Alpha 0.6.0.

### Alpha 0.6.0: Club Advisor Foundation

Future sprint. Not started. Configurable Club DNA is explicitly out of scope until
this sprint at the earliest.

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
