# Club Advisor

Alpha 0.6.0 introduces the first club-level intelligence layer: a summary of the
current state of the sporting project and its most important priorities, built
entirely from evidence already produced by Squad Intelligence and Training. The
Club Advisor does not replace the manager and does not make decisions — it helps
the manager make better ones.

## Purpose

> Match answers "which lineup should I use?" Training answers "who receives
> training?" Squad answers "what role does every player fulfill?" Club Advisor
> answers: how healthy is the project, what are the biggest risks, and what
> should the priorities be this week?

## Reference strategy

Same as Squad Intelligence: `SUSTAINABLE_GROWTH`, the only implemented strategy.
No strategy selector, no configurable Club DNA, no promotion or aggressive
transfer strategies — the Advisor evaluates everything assuming long-term
sustainable growth.

## Inputs

The Club Advisor **never recomputes** a player's role, rating, or training fit —
it only aggregates outputs that already exist:

- **Squad Intelligence**: every current player's `PlayerIntelligenceReport`
  (recommended role, training fit, salary efficiency, and so on).
- **Training System**: the active training type, read the same way Squad
  Intelligence reads it — via the canonical catalog, never duplicated.
- **Squad-relative context**: positional depth and age-by-position, already
  built by `SquadIntelligenceAppService.build_squad_context()`.

Official Match Intelligence, Historical Match Foundation, Historical Evolution
and Historical Insights are supported as *optional* future inputs
(`ClubAdvisorContext.has_historical_data`, `evolution_result`, `insights_result`)
but this sprint's app-layer bridge doesn't populate them yet — their absence is
disclosed as an honest limitation (`HISTORICAL_DATA_UNAVAILABLE`), never silently
ignored or faked.

## Architecture

`engine/club_advisor/` — Qt- and localization-independent:

- `enums.py`: `ProjectStatus` (5 values), `PriorityType` (8), `ClubStrengthType`
  (6), `ClubRiskType` (8), `ClubWarningType` (6), `ClubConfidence` (4),
  `ClubLimitationType` (8), `DepthStatus` (5).
- `context.py`: `ClubAdvisorContext` — holds only already-computed inputs (Squad
  Intelligence reports, squad-relative context, active training type).
- `summary.py`: `build_training_summary` / `build_squad_summary` /
  `build_depth_summary` / `build_sporting_summary` — pure aggregations, each a
  simple count/classification over the already-computed `squad_reports` and
  `squad_context.positional_depth`. No new rating is computed anywhere here.
- `dimensions.py`: `evaluate_project_status` — see "Project status" below.
- `priorities.py` / `strengths.py` / `risks.py` / `warnings.py`: independent
  detector functions, each returning zero or more evidenced findings. Unlike
  Squad Intelligence's role/status rules (which pick exactly one winner), every
  Club Advisor detector may fire independently and all its findings are kept.
- `confidence.py`: the same documented-policy style as Squad Intelligence and
  Historical Insights.
- `rule_engine.py`: `ClubAdvisorRuleEngine.evaluate()` — thin, explicit
  orchestration (build summaries, then run every detector against them).
- `service.py`: `generate_report()` — the only function most callers need.

Application layer:

- `ht_coach_app/services/club_advisor_service.py`'s `ClubAdvisorAppService`
  bridges the current roster into `ClubAdvisorContext`, reusing
  `SquadIntelligenceAppService` rather than rebuilding roster/training context a
  second time.
- `ht_coach_app/services/club_advisor_formatting.py`: stable
  enum-to-localization-key mapping.

## Outputs

`ClubAdvisorReport`: project status, ordered priorities, strengths, risks, a
training/squad/depth/sporting summary, warnings, confidence, limitations, and a
flat evidence trail. **There is no `overall_score` field** — a structural
guarantee (covered by `test_report_never_shows_a_single_overall_score`), not
just a convention.

## Project status

`ProjectStatus` is deliberately **not** computed from a single blended score.
`dimensions.evaluate_project_status()` evaluates three genuinely independent
sub-assessments — training utilization health, positional depth health, and
squad composition health — and the *worst* one caps the overall status. A club
can't be called "Excellent" if any one of those three is in trouble, even if the
other two are perfect; see
`test_project_status_never_uses_a_single_blended_score` for the regression test
proving this isn't secretly an average.

## Evidence model

Every priority, strength, risk and warning carries `ClubEvidence` — the same
"every conclusion needs a traceable fact" discipline used throughout HT Coach's
domain layers since the Historical Insights Engine. Warnings additionally carry
a `reason_key` + `reason_params`, since the brief specifically requires warnings
to explain *why* ("Only 1 goalkeeper is on the roster; an injury would leave the
team without options" rather than just "No goalkeeper backup").

## Priority generation

Priorities are ordered by an internal urgency ranking (goalkeeper coverage and
positional-depth gaps rank highest; "maintain current training" ranks lowest,
since it's a steady-state recommendation rather than an urgent one), then
assigned a 1-based `rank`. **Priorities never recommend a purchase, a specific
player, or a transfer price** — the catalog (`PriorityType`) is entirely
composed of internal-management actions (train, monitor, develop, review), and
this is enforced by `test_priorities_never_mention_purchases_or_prices`.

## Known limitations

Five limitations are **always present** in every report, by design — this
sprint has no financial, league-comparison, transfer-market, salary-budget, or
promotion-target data source at all:

- `FINANCIAL_DATA_UNAVAILABLE`
- `LEAGUE_COMPARISON_UNAVAILABLE`
- `TRANSFER_MARKET_UNAVAILABLE`
- `SALARY_BUDGET_UNAVAILABLE`
- `PROMOTION_TARGET_UNKNOWN`

Two more appear conditionally: `EMPTY_ROSTER` (no players to evaluate) and
`NO_ACTIVE_TRAINING` (no training context to evaluate training-related
sections against). `HISTORICAL_DATA_UNAVAILABLE` appears whenever
`has_historical_data` is `False` — which is always true today, since the
app-layer bridge doesn't wire up History yet (see "Inputs" above).

## UI

A new "Club Advisor" navigation tab (`ht_coach_app/views/club_advisor_page.py`,
`ht_coach_app/controllers/club_advisor_controller.py`) — the first genuinely new
top-level page introduced since the original module set, deliberately kept
simple: a "Generate report" button reads the roster CSV already remembered by
Squad's workspace settings, then renders one concise card per section (Project
Status, Priorities, Strengths, Risks, Training, Squad, Depth, Warnings,
Limitations). No charts, no gauges, no overall score anywhere on the page.

## Responsibility boundaries

- Never invokes `FormationOptimizer`, `TacticOptimizer` or `LineupOptimizer`
  (static-import test).
- Never imports `PlayerRatingEngine` or `PlayerAnalyzer` directly (static-import
  test) — current performance, training fit and every other player-level fact
  come from Squad Intelligence's already-computed reports, never recalculated.
- Training's canonical catalog is reused via Squad Intelligence, never
  duplicated a third time.
- No financial affordability calculation, no market-price estimation, no
  automatic sale or purchase recommendation.

## Future roadmap

This sprint is explicitly a *foundation*. Deliberately deferred:

- Wiring `has_historical_data` / `evolution_result` / `insights_result` to a
  real History adapter, so the Advisor can eventually say things like "training
  utilization has improved over the last 3 weeks" using Historical Evolution.
- A Transfer Planner or Financial Planner that could eventually replace the
  "always present" financial/transfer/budget limitations with real evidence.
- Configurable Club DNA (multiple reference strategies instead of the single
  `SUSTAINABLE_GROWTH` implementation).
- League analysis and promotion planning.

None of these require redesigning what's built here: `ClubAdvisorContext` and
`ClubAdvisorReport` already have the shape to grow into them.
