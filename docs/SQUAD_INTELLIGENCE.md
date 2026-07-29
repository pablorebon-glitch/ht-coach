# Squad Intelligence

Alpha 0.5.9.1 turns Squad from a roster-data screen into a player-management
intelligence screen: for any current-roster player, HT Coach now produces a
deterministic, explainable classification of who they are within the sporting
project, what to do with them, and why — all within five seconds of reading, and
without exposing a raw "Overall: 87" score anywhere.

## Product decision supported

> Hattrick is the source of truth. HT Coach helps the manager understand who each
> player is, what role they fulfill, whether they fit the active training, and
> whether they should be developed, retained or reviewed — with evidence, not
> opinion.

## Reference club strategy

The only implemented strategy this sprint is `SUSTAINABLE_GROWTH`: develop the
squad gradually, prioritize training value, maintain healthy salaries, avoid
expensive short-term promotion pushes, preserve useful starters, and sell only
when sporting, training and economic context justify it.

There is no strategy selector and no onboarding — `ClubStrategy` is a typed,
single-member enum today, read from context by every rule rather than hardcoded,
specifically so a future sprint can make it configurable (multiple strategies)
without redesigning the engine.

## Architecture

`engine/squad_intelligence/` — Qt-independent, localization-independent:

- `enums.py`: every stable value this sprint introduces (`ClubStrategy`,
  `RecommendedRole`, `ManagementStatus`, the five dimension enums, `MilestoneType`,
  `IntelligenceConfidence`, `StrengthType`, `RiskType`, `LimitationType`).
- `evidence.py`: `IntelligenceEvidence` — the same "every conclusion needs a fact
  behind it" discipline as the Historical Insights Engine.
- `context.py`: `PositionEvidence`, `TrainingEvidence`, `PlayerIntelligenceContext`,
  `SquadIntelligenceContext` — everything a rule may read, built once per batch
  analysis rather than recomputed per rule.
- `scoring.py`: internal normalized [0, 1] scores (`match_value`,
  `training_fit_value`, `training_value`, `salary_efficiency_value`,
  `strategic_value_score`, `replacement_difficulty`) and `ScoringThresholds`
  (typed, documented, constructor-validated — never a hidden magic constant
  inside a rule).
- `dimensions.py`: the five classifiers (`classify_current_performance`,
  `classify_training_potential`, `classify_training_fit`,
  `classify_salary_efficiency`, `classify_strategic_value`), each returning a
  qualitative category plus the evidence that produced it.
- `roles.py` / `statuses.py`: one rule class per role/status (never one giant
  if/elif chain), each returning at most one `(value, priority, evidence)`
  candidate; a guaranteed fallback rule (`DepthPlayerRule` / `MonitorStatusRule`)
  ensures every player gets exactly one primary role and one status.
- `milestones.py`: deterministic next-milestone selection — never an exact
  calendar date, never an invented skill sub-level.
- `warnings.py`: `detect_strengths` / `detect_risks`, capped at 3 visible items
  each, always with evidence attached.
- `confidence.py`: the same style of documented, deterministic confidence policy
  as the Historical Insights Engine.
- `rule.py` / `rule_engine.py`: `RoleEvaluationContext`, `RoleRule` / `StatusRule`
  base classes, and `SquadIntelligenceRuleEngine`, which picks the
  highest-priority match (ties broken by rule ID) for role, then for status given
  the resolved role.
- `service.py`: `generate_report()` (one player) and `generate_squad_reports()`
  (deterministic batch analysis for the whole squad) — the only two functions
  most callers need.

Application integration:

- `ht_coach_app/services/squad_intelligence_service.py`'s
  `SquadIntelligenceAppService` builds `PlayerIntelligenceContext` /
  `SquadIntelligenceContext` from the current roster, reusing the app's existing
  positional-ranking infrastructure (`PlayerAnalyzer` / `SquadService`) and the
  canonical training catalog (`rule_provider_for`) — never a second rating engine,
  never a duplicated training matrix.
- `ht_coach_app/services/squad_intelligence_formatting.py`: stable
  enum-value-to-localization-key mapping (`role_label_key`, `status_label_key`,
  etc.) — domain rules never assemble English or Spanish sentences themselves.

## Core result model

`PlayerIntelligenceReport` (frozen dataclass, `engine/squad_intelligence/models.py`):
recommended role, management status, primary reason (key + params), up to 3
supporting reasons, the five visible dimensions, strengths, risks, next milestone,
full evidence trail, confidence, limitations, engine version. **There is no
`overall_score` or `score` field on this dataclass** — a structural guarantee, not
just a convention, and it's covered by a dedicated test
(`test_report_never_shows_a_raw_overall_score`).

## Role catalog

`KEY_STARTER`, `STARTER`, `PRIMARY_TRAINEE`, `SECONDARY_TRAINEE`,
`TACTICAL_SPECIALIST`, `USEFUL_ROTATION`, `DEVELOPMENT_PROJECT`, `VETERAN_MENTOR`,
`DEPTH_PLAYER`, `TRANSFER_CANDIDATE`, `REPLACEABLE`. Every player receives exactly
one, via `DepthPlayerRule`'s guaranteed lowest-priority fallback.

**Documented conflict resolution:** a player who is both a very-high current
performer and hard to replace, and who also has excellent training fit with a
required priority, could plausibly be classified as either `KEY_STARTER` or
`PRIMARY_TRAINEE`. This sprint resolves that deterministically in favor of
`KEY_STARTER` (`roles.py`'s `KeyStarterRule`, priority 95, ahead of
`PrimaryTraineeRule`'s priority 90): being currently irreplaceable is treated as
more urgent than training status. The same player's excellent training fit is
still fully visible in the report's `training_fit` dimension and evidence — the
role resolution doesn't hide it, it just doesn't become the *primary* label.

## Management status catalog

`KEEP`, `TRAIN`, `MONITOR`, `REVIEW_AT_NEXT_SKILL_LEVEL`, `EVALUATE_SALE`,
`MAINTAIN_AS_DEPTH`, `GRADUALLY_REPLACE`, `DO_NOT_INVEST_MORE_TRAINING`.

There is **no unconditional "sell" status**. `EVALUATE_SALE` is the strongest
transfer-related signal this sprint produces — the engine doesn't yet know club
finances, market prices, replacement cost, transfer deadlines or league
objectives, so an immediate-sale order would be unsupported. That belongs to a
future Club Advisor / Transfer Advisor.

## Visible dimensions

Five qualitative categories, never raw scores:

- **Current performance** (`VERY_HIGH`…`VERY_LOW`, `INSUFFICIENT_DATA`): built from
  the app's existing positional ranking (`PlayerAnalyzer`), modified by form and
  stamina, capped low when the player is unavailable. Salary is never used as a
  performance signal.
- **Training potential** (`VERY_HIGH`…`LOW`, `EXHAUSTED`, `NOT_APPLICABLE`,
  `INSUFFICIENT_DATA`): combines training fit with an age-based development-runway
  factor, so an old player in a fully-fitting slot is `EXHAUSTED`, not `VERY_HIGH`
  — occupying a trainable position is not enough on its own.
- **Training fit** (`EXCELLENT`…`NO_TRAINING`, `UNKNOWN`): read directly from the
  canonical Complete Training System (Alpha 0.5.8.5) via `rule_provider_for` — the
  same `FULL`/`REDUCED`/`VERY_SMALL`/`NONE` effect tiers, never a second matrix.
- **Salary efficiency** (`EXCELLENT`…`VERY_LOW`, `INSUFFICIENT_DATA`):
  squad-relative — a high salary stays efficient when usefulness matches it; a low
  salary is not automatically excellent if the player isn't actually useful.
- **Strategic value** (`KEY`…`LOW`, `INSUFFICIENT_DATA`): combines current
  usefulness, training value, replacement difficulty and salary efficiency — the
  same moderate player can be `KEY` when no replacement exists at their position
  and `LOW`/`MEDIUM` when several do, because `replacement_difficulty` reads
  squad-relative positional depth from `SquadIntelligenceContext`.

## Salary-efficiency limitations

Salary efficiency is computed **squad-relative** (percentile within the current
roster's salaries), not against club income or affordability — that requires
financial context this sprint deliberately does not model (see Guardrails). A
player's salary percentile with no salary_values in the squad context (e.g. an
empty roster) yields `INSUFFICIENT_DATA`, never a guess.

## Strategic-value model

See `scoring.strategic_value_score`: a weighted combination of current match
value, training value, replacement difficulty and salary efficiency, using
whichever components are actually available (missing ones don't crash the
calculation, they're simply excluded from the weighted average).

## Evidence and confidence

Every visible conclusion carries `IntelligenceEvidence` — entity, value, and a
localization key for its label. Confidence (`classify_confidence`,
`confidence.py`) is deterministic: `HIGH` requires a positional score, active
training, salary and a stable player ID with no contradictions; `MEDIUM` and `LOW`
degrade gracefully as inputs go missing; `INSUFFICIENT_DATA` only when the player
truly can't be evaluated (no positional score *and* no training evidence at all).
Missing historical data alone never blocks classification — History is optional
context, never a requirement.

## Milestone policy

Deterministic, never a calendar date, never an invented skill sub-level:
`REACH_TRAINED_SKILL_LEVEL` (primary trainees with very-high potential),
`REVIEW_AT_AGE` (veteran mentors, next age), `REVIEW_AFTER_TRAINING_CYCLE`
(secondary trainees / development projects), `REVIEW_AFTER_MATCHES` (rotation /
depth players, a fixed configurable match count), `REVIEW_WHEN_REPLACEMENT_EXISTS`
/ `REVIEW_WHEN_SALARY_THRESHOLD_CONTEXT_EXISTS` (replaceable / transfer
candidates, depending on positional scarcity), `NO_MILESTONE` (settled cases),
`INSUFFICIENT_DATA` (when confidence itself is insufficient).

## Training integration

Squad Intelligence never duplicates the training matrix. `TrainingEvidence` is
built by calling `rule_provider_for(active_training_type)` and, for the player's
best position, either `effect_for_position()` (the generalized `CatalogTrainingRules`
path) or `factor_for_position()` (Playmaking's untouched original class) — the same
generalized-training-system entry point Alpha 0.5.8.5 and UX-02 already exposed in
the Planner. A training-type change recalculates the currently-shown report
immediately (see UI Integration below); it never hardcodes Playmaking.

## UI integration

No new top-level navigation page. The existing Squad "Jugadores" tab's player
selection (already wired to `player_selected` → `_show_player_detail`) now also
triggers `SquadIntelligenceAppService.generate_report()` and renders a compact
panel directly below the existing player-detail widgets, in the requested content
order: recommended role, status, primary reason, the five dimensions, strengths,
risks, next milestone, evidence, limitations. Changing the active training type
recalculates the currently-shown player's report immediately, without requiring a
re-selection. No CSV selector was added (Squad remains the sole CSV-loading
workflow), and no "Generate Lineup" action exists here.

## Responsibility boundaries

- Squad owns roster loading and hosts Squad Intelligence.
- Match remains the only formation/order optimizer; Squad Intelligence never
  invokes `FormationOptimizer` or `TacticOptimizer` — enforced by a static-import
  test (`tests/test_squad_intelligence_engine.py::test_squad_intelligence_never_imports_formation_optimizer`)
  scanning every file in `engine/squad_intelligence/`.
- Training's canonical catalog is reused, never duplicated.
- History, when available, only supplies read-only evidence; it's never required
  and never mutates current classifications.
- No financial affordability calculation, no market-price estimation, no
  automatic sale order — those remain explicitly out of scope for a future Club
  Advisor.

## Future Club Advisor integration

Alpha 0.6.0 (Club Advisor Foundation) is expected to aggregate every player's
`PlayerIntelligenceReport` across the squad into club-level recommendations (e.g.
"3 players are EVALUATE_SALE and share a position — consider consolidating"),
combine it with financial context this sprint deliberately doesn't model, and
potentially make `ClubStrategy` genuinely configurable. Nothing in this sprint's
architecture needs to change for that: `generate_squad_reports()` already returns
every player's full report, ready to be aggregated.
