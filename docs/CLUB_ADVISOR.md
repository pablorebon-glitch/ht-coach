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

## Need vs. Urgency (Alpha 0.6.2)

The single most important addition this sprint makes: **a structural need does
not automatically imply an immediate action.** A club can have weak defensive
depth while simultaneously being dominant in its current league, facing several
bot opponents, having just signed an expensive defender, and treating promotion
as "welcome if natural" rather than a target. All of that context should lower
the *urgency* of acting on the defensive gap -- but it must never erase the
underlying *need* to eventually address it.

Two genuinely independent dimensions:

- **`StrategicNeed`** (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`/`NONE`/`INSUFFICIENT_DATA`)
  answers "how important is it for the club to address this eventually?" —
  derived entirely from structural evidence Club Advisor's existing engine
  already computed (positional depth status, training utilization ratio,
  veteran concentration). Season context **never** changes this.
- **`OperationalUrgency`** (`IMMEDIATE`/`HIGH`/`MEDIUM`/`LOW`/`DEFERRED`/`NONE`/`INSUFFICIENT_DATA`)
  answers "how soon must the club act?" — computed from `StrategicNeed` *and*
  `SeasonContext` together (`engine/club_advisor/urgency.py`'s `compute_urgency`),
  never from need alone.

`compute_urgency` starts from a documented "prior" (need's baseline urgency,
already one tier gentler than a naive need-equals-urgency reading) and applies
named, evidenced reducers (strong/dominant current competitiveness, several bot
opponents, early season, a recent relevant signing, promotion not prioritized)
and increasers (no internal replacement, an unavailable player, late
season/promotion stage, promotion explicitly targeted). Critically, **a genuine
need can never be reduced all the way to nothing**: a documented floor per need
tier (e.g. `HIGH` need can never be reduced below `LOW` urgency) keeps
"high need, low urgency" from silently collapsing into "no need to look at this
at all" — this is what makes "monitor" a meaningfully different recommendation
from "do nothing."

`engine/club_advisor/timing.py`'s `determine_action_type` is the **only** place
need and urgency are combined into one recommended `ActionType`
(`ACT_NOW`/`MAINTAIN`/`MONITOR`/`PREPARE`/`REEVALUATE`/`DEFER`/`NO_ACTION`).
The sprint's own worked example — central-defense depth with `HIGH` need and
`LOW` urgency — is reproduced exactly:
`tests/test_club_advisor_season_aware.py::test_scenario_1_high_need_low_urgency_monitors_or_defers`
and the real-data regression fixture both verify this.

## Strategic vs. Operational Priorities

Every area Club Advisor tracks (goalkeeper succession, central-defense depth,
training utilization, veteran succession) can produce **two** differently
framed recommendations:

- A **strategic** priority: the longer-term structural statement ("goalkeeper
  succession needs planning eventually").
- An **operational** priority: the actual recommended action for *this*
  season, using the real computed urgency/action/horizon ("monitor central
  defense; no purchase justified right now; review before promotion").

The same area never repeats identical text between the two lists — they use
different `reason_key`s by design.

## Recommendation Horizons

Every `ClubPriority` has a `RecommendationHorizon`
(`THIS_WEEK`/`NEXT_MATCHES`/`CURRENT_SEASON`/`BEFORE_PROMOTION`/`NEXT_SEASON`/
`LONG_TERM`/`WHEN_CONDITION_CHANGES`/`NO_ACTION_REQUIRED`),
derived from its `ActionType` (`engine/club_advisor/horizons.py`) and sharpened
by season context: a `MONITOR`/`REEVALUATE` action becomes `BEFORE_PROMOTION`
when promotion is actually being targeted, and an age-driven ("future
shortage") depth concern becomes `NEXT_SEASON` rather than `CURRENT_SEASON`,
since a succession question is a roster-planning concern, not a mid-season one.

## Deliberate Inaction

"No additional signing is currently required" is a legitimate, first-class
recommendation — not an absence of intelligence. Whenever training utilization
is already healthy, the operational list includes a `MAINTAIN_CURRENT_TRAINING`
priority with its own evidence, exactly like every other recommendation. The
same principle extends through the `NO_ACTION`/`DEFER` action types more
generally: a `LOW` need that reduces to `NONE`/`DEFERRED` urgency produces
`NO_ACTION`, always with supporting evidence, never silence.

## Season Context

`SeasonContext` (`engine/club_advisor/season_context.py`) is a fully optional,
typed input — every field may be unknown, and this sprint never fabricates a
missing value. `promotion_objective` defaults to `WELCOME_IF_NATURAL` (a
season-level planning input, not configurable Club DNA — there is still only
one implemented `ClubStrategy`, `SUSTAINABLE_GROWTH`). A compact "Season Plan"
configuration lives directly in the Club Advisor page (season phase, promotion
objective, current competitiveness, bot opponent count, a recent-major-signing
checkbox, free-text notes) — no wizard, no required fields.

`generate_report()` accepts `season_context` as an entirely optional keyword
argument; omitting it still produces strategic/operational priorities and a
promotion-readiness assessment, just reflecting an unknown/default context
(lower confidence, more limitations) rather than crashing or fabricating
season-level conclusions.

## Recent-Signing Policy

A recently completed signing in the same area as a structural need is treated
as *evidence that reduces urgency*, never as evidence that erases the need
itself. `SeasonContext.signing_matches_area()` matches a recorded
`recent_signing_position` (e.g. `"CENTRAL_DEFENDER"`) against an area name; a
match feeds `UrgencyInputs.area_matches_recent_signing` into `compute_urgency`,
applying exactly one reducer step — the same floor-protected mechanism as every
other reducer, so a `HIGH` need with a matching recent signing still can't drop
below `LOW` urgency on that basis alone. No transfer cost, market value or
affordability is ever estimated — `SigningCostCategory`
(`LOW`/`MODERATE`/`HIGH`/`VERY_HIGH`/`UNKNOWN`) is a coarse, optional
qualitative tag only.

## Promotion Readiness (Preliminary, Not a Simulator)

`PromotionReadiness` (`READY`/`NEARLY_READY`/`DEVELOPING`/`NOT_READY`/
`NOT_EVALUATED`) is explicitly preliminary — this sprint does not build a
target-division simulator. `assess_promotion_readiness()`
(`engine/club_advisor/recommendation_policy.py`) uses only what's already
available: positional depth gaps (`NO_REPLACEMENT`/`FUTURE_SHORTAGE`) and
current competitiveness. **Current-league dominance never implies promotion
readiness by itself** — the sprint's own core distinction: a squad that
comfortably dominates its current league but still has a genuine depth gap is
`DEVELOPING`, not `READY`, and the reason explicitly says so. Confidence is
always `INSUFFICIENT_DATA` (readiness `NOT_EVALUATED`) whenever current
competitiveness itself is unknown — never a guessed readiness. A
`LEAGUE_COMPARISON_UNAVAILABLE` limitation is always attached, since this
sprint has no data about the target division at all.

## Structural vs. Temporary (Alpha 0.6.3)

A defender injured for four weeks does not mean "no central defender depth" if
the club still owns enough players — a short-term absence and a genuine
structural gap are different facts, and conflating them was a real grounding
problem this sprint fixes.

Two explicit layers:

- **Structural club status** uses the *complete* roster — an unavailable
  player still counts as a real, owned player. This is what `positional_depth`
  has always meant.
- **Temporary availability** reflects only players available *this week* —
  `SquadIntelligenceContext.temporary_positional_depth`, built from the
  existing `AvailabilityService` (never a new availability engine).

`PositionDepth` now carries both: `player_count`/`status` (structural) and
`temporary_count`/`temporary_status` (this week only), plus
`has_reduced_temporary_availability` — true only when the two genuinely
differ. A new `REDUCED_TEMPORARY_AVAILABILITY` warning fires from that flag,
kept entirely separate from the structural `WEAK_POSITIONAL_DEPTH` risk.

## Formation-Aware Depth

Depth conclusions now read against what the manager actually plays, not a flat
replacement count. `formation_position_maximums()` (built for the Training
Priority Wizard in Alpha 0.6.1, reused here rather than duplicated) gives the
maximum legal count of a position across every canonical formation — so a
manager who consistently plays 2-5-3 doesn't get told they need four or five
starting central defenders. The central-defense risk (see below) explicitly
compares combined central-defender-plus-wing-back coverage against this
formation demand before deciding whether the gap has real match-day impact.

## Training-Aware Projects

A player's *current* best position and their *future* training project
coexist — they are not mutually exclusive. A Wing Back currently starting
every week can simultaneously be a deliberate Playmaking trainee being
developed toward Inner Midfielder. `_is_training_project()`
(`engine/club_advisor/summary.py`) flags this independently of
`recommended_role`: any player whose `training_fit` is
`EXCELLENT`/`COMPATIBLE`/`PARTIAL` *and* whose `training_potential` is
`MEDIUM` or higher counts as a project, regardless of what role they're
currently playing. This fixed a real reporting bug (Part 4 of this sprint):
"Projects: 0" when developing players clearly existed.

## Club Advisor Uses the Weekly Planner as Source of Truth

The training summary (active training, primary/secondary trainee counts,
players without training) is built entirely from Squad Intelligence's
already-computed reports, which themselves read training fit through the
canonical Training catalog and the Weekly Planner's own priority records —
never re-derived independently. `TRAINING_CAPACITY_UNDERUSED`,
`PRIORITY_TRAINEES_MISSING_TRAINING`, `TRAINING_SLOT_COMPETITION` and
`TRAINING_PLAN_DEVIATION` are all read the same way.

## Detailed Risks, Not Abstract Labels

Every `ClubRisk` now carries `position`, `reason_key`/`reason_params`,
`impact`, `urgency`, `affected_players` (real names, from
`ClubAdvisorContext.players_by_position`), and `review_condition_key` — never
just an abstract "Weak positional depth" label. The central-defense risk is
the clearest example of formation-awareness changing the actual conclusion:
if combined central-defender-plus-wing-back coverage still clears what the
preferred formations field, `impact` is `low` even though the position itself
shows no direct replacement — matching this sprint's own worked example
exactly (Roberto + Jae covering a 2-5-3 formation, one temporary injury,
impact low).

## Training Warnings, Not Training Risks

Per this sprint's explicit instruction: a position sitting outside the active
training's effect is often entirely expected (e.g. Playmaking simply doesn't
train goalkeepers) and must never be reported as a squad-structure risk.
`PLAYERS_WITHOUT_TRAINING` and `TOO_MANY_PLAYERS_PER_TRAINING_SLOT` were moved
out of `risks.py` entirely; the training-plan-specific concerns they used to
conflate with genuine squad risks now live in `warnings.py` as
`PLAYERS_NOT_RECEIVING_TRAINING`, `PRIORITY_TRAINEES_MISSING_TRAINING` (a
player Squad Intelligence flagged as a trainee but who isn't actually getting
the training effect), `TRAINING_SLOT_COMPETITION`, and
`TRAINING_PLAN_DEVIATION` (a player receiving the full training effect despite
not being a flagged trainee, starter, or tactical specialist — worth a look,
not necessarily a problem).

## Every Count Is Also a Player List

`SquadSummary` now carries the actual player names behind every count
(`key_starter_players`, `rotation_players`, `development_project_players`,
`transfer_candidate_players`, `replaceable_players`, `veteran_players`,
`depth_players`) — a manager can always see who's behind a number, not just
the number.

## Card Drill-Down UX

Clicking any card (Squad, Training, Depth, Risks, Strengths, Limitations) on
the Club Advisor page opens a centered modal
(`ht_coach_app/widgets/drilldown_overlay.py`'s `DrillDownOverlay`) over a
translucent full-page overlay: a clickable list on the left (first row
selected by default), full detail on the right. Closes via the Close button,
Escape, or a click outside the centered panel. Each card defines its own
drill-down content (e.g. Risks shows reason/impact/urgency/affected
players/review trigger per risk; Squad shows the actual player list per
category), reusing the exact same report data already shown on the card —
never a second calculation.

**HF-02.2 fixes.** Two real bugs, found and fixed: (1) `#drillDownPanel` had
no CSS rule of its own at all, so it silently inherited the translucent grey
overlay behind it instead of showing an opaque white surface — the stylesheet
now explicitly styles the panel, its list, and its detail area as solid white,
with a subtle drop shadow and a small × close control (never a large "Cerrar"
button). (2) the Training drill-down showed player *counts*
(`"3 players"`) instead of actual names. `TrainingSummary` gained
`full_priority_players`/`half_priority_players`/`covered_players`/
`uncovered_priority_players` — real name tuples derived directly from
`ClubAdvisorContext.training_priority_rows` (the Weekly Planner's own priority
records) cross-referenced against `coverage_rows` for the covered/uncovered
split. Groups with no players show an explicit "no players in this group"
message rather than a generic "no detail available" placeholder.

## Project Status Explanation

Never show "Critical" (or any status) without saying why.
`dimensions.explain_project_status()` identifies which of the three
independent health dimensions (training/depth/squad composition) actually
drove the overall status, and separately reads the season-aware operational
priorities to answer "does this also require acting now, or is the structural
weakness already being handled with low urgency?" — applying Alpha 0.6.2's
need-vs-urgency distinction to the headline status itself, not just individual
priorities.

## Future roadmap

Alpha 0.6.0 was explicitly a *foundation*; Alpha 0.6.2 delivered the season-aware
priority/urgency/timing layer promised there. Still deliberately deferred:

- **A real League Intelligence integration.** `CurrentCompetitiveness` and
  `estimated_league_strength`/`direct_rival_strength` remain free-text/manual
  inputs this sprint — there is no automated Hattrick league import, CHPP/API
  integration, or opponent scraping. A future sprint could compute
  competitiveness from Match Intelligence's own official-rating comparisons
  instead of asking the manager to classify it by hand.
- Wiring `has_historical_data` / `evolution_result` / `insights_result` to a
  real History adapter, so the Advisor can eventually say things like "training
  utilization has improved over the last 3 weeks" using Historical Evolution.
- A Transfer Planner or Financial Planner that could eventually replace the
  "always present" financial/transfer/budget limitations with real evidence.
- Configurable Club DNA (multiple reference strategies instead of the single
  `SUSTAINABLE_GROWTH` implementation) — `PromotionObjective` remains a
  season-level planning input, not a second Club DNA system.
- A real target-division simulator for `PromotionReadiness` (this sprint's
  assessment is deliberately preliminary and evidence-limited).

None of these require redesigning what's built here: `ClubAdvisorContext`,
`ClubAdvisorReport` and `SeasonContext` already have the shape to grow into them.
