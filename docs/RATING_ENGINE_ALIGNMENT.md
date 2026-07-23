# Rating Engine Alignment Audit

Alpha 0.5.6 audits whether HT Coach lineup sector values can be represented on the
same decimal scale used by Hattrick match ratings.

Final classification: **C**.

The current repository does not contain enough evidence to prove that HT Coach internal
sector values are exact Hattrick quarter-step ratings or that they can be converted to
Hattrick decimal ratings through an existing deterministic representation. Direct
comparison therefore remains unavailable.

## Pipeline Diagram

```text
Player skill values
  -> PlayerPerformance.effective_skill(player, skill)
       base skill * form factor
  -> ContributionCalculator.calculate(player, position, side)
       weighted sector contributions from POSITION_COEFFICIENTS
  -> OrderModifier.apply(contribution, position, side, order, order_side)
       order-specific multiplicative sector factors
  -> TeamCalculator.calculate(contributions)
       additive sector totals
  -> TeamRater.calculate(lineup)
       TeamRatings / Contribution-like sector values
  -> FormationAnalyzer.overall_score(ratings)
       sum of seven main sector totals for formation ranking context
  -> MatchWorkspaceService result mapping
       serializable view model and sector calibration rows
  -> PySide6 Match page
       raw internal values shown as internal contribution ratings
```

## Relevant Files

- `models/player.py`: stores numeric player skills, form, stamina, experience,
  leadership, TSI and salary.
- `engine/performance/player_performance.py`: computes form-adjusted effective skills.
- `engine/config/coefficients.py`: position-to-sector skill weights.
- `engine/calculators/contribution_calculator.py`: builds per-player sector
  contributions.
- `engine/orders/order_modifier.py`: applies individual-order multipliers.
- `engine/calculators/team_calculator.py`: adds contribution objects.
- `engine/analyzers/team_rater.py`: orchestrates position engines, order modifiers and
  team aggregation.
- `engine/analyzers/formation_analyzer.py`: sums sector values for an overall formation
  score.
- `models/team_ratings.py`: stores seven main sectors plus optional indirect ratings.
- `engine/ratings/sector_rating.py`: labels rating source scales and blocks arithmetic
  across incompatible scales.
- `engine/ratings/rating_alignment.py`: typed audit concepts, Hattrick decimal
  descriptive mapping, candidate conversion helpers and diagnostics.
- `ht_coach_app/services/opponent_ratings_clipboard_parser.py`: imports Hattrick
  decimal opponent ratings without changing their values.

## Formulas Present In The Repository

Player form factor:

```text
factor = 1.0 + (form - 7) * 0.05
clamped between 0.50 and 1.20
```

Effective player skill:

```text
effective_skill = base_skill * form_factor
```

Per-position contribution:

```text
sector_contribution = sum(effective_skill(skill) * coefficient)
rounded to 2 decimals at the player-position contribution stage
```

Order modifier:

```text
modified_sector = contribution_sector * order_factor
rounded to 2 decimals after order application
```

Team sector total:

```text
team_sector = sum(player_sector_contribution for selected lineup players)
```

Formation overall score:

```text
left_defense
+ central_defense
+ right_defense
+ midfield
+ left_attack
+ central_attack
+ right_attack
```

No formula in the audited path divides internal sector totals by 4, multiplies them by
4, computes quotient/remainder sublevels, floors to Hattrick quarter steps, or maps
internal sector totals to Hattrick descriptive labels.

## Intermediate Value Meanings

Player skill values are numeric skill inputs from the roster CSV.

Effective skill values are form-adjusted player skill values. They are continuous
numbers, not Hattrick sector ratings.

Player contribution values are weighted sector contributions for a specific position and
side. They are rounded to two decimals and may be fractional values such as `11.20`.

Order-adjusted contribution values are the same contribution totals after applying
individual-order multipliers. They are also rounded to two decimals.

TeamRater sector values are additive sums of player contributions. They are internal
team contribution totals used by the engine and optimizer stack.

FormationAnalyzer overall score is a sum of internal sector totals used as a broad
formation-fit score. It is not a Hattrick match rating.

## Values Such As 45, 29, 38 And 27

Values such as:

- midfield: `45`
- left attack: `29`
- central attack: `38`
- right attack: `27`

are best classified as **HT Coach internal contribution totals**.

They are produced by additive weighted player contributions after form and order
modifiers. They are not currently proven to be Hattrick quarter-step indices or Hattrick
decimal ratings.

## Rounding Behavior

- `ContributionCalculator` rounds each player-position sector contribution to two
  decimals.
- `OrderModifier` rounds modified sector contributions to two decimals.
- `TeamCalculator` adds the rounded contribution values and does not apply a Hattrick
  quarter-step rounding policy.
- `format_rating_value` displays internal values with zero decimals and Hattrick decimal
  values with two decimals.
- Hattrick decimal descriptive mapping in the audit helper accepts only `.00`, `.25`,
  `.50` and `.75` sublevels.

## Hattrick Decimal Scale

Imported opponent values are treated as authoritative Hattrick decimal values.

The reference fixture `pata2008` uses:

| Sector | Decimal |
| --- | ---: |
| Midfield | 5.25 |
| Right defense | 6.75 |
| Central defense | 7.00 |
| Left defense | 5.50 |
| Right attack | 5.25 |
| Central attack | 4.50 |
| Left attack | 4.00 |
| Indirect defense | 7.00 |
| Indirect attack | 6.50 |

Observed descriptive semantics:

| Decimal | Label |
| ---: | --- |
| 4.00 | weak - very low |
| 4.25 | weak - low |
| 4.50 | weak - high |
| 4.75 | weak - very high |
| 5.00 | inadequate - very low |
| 5.25 | inadequate - low |
| 6.75 | passable - very high |
| 7.00 | solid - very low |

The parser stores decimal values directly and does not derive them from labels.

## Candidate Conversion Analysis

Hypothesis: `decimal = internal / 4 + offset`.

This family is monotonic when offset is fixed and produces `.25` increments for integer
internal values. It is not sufficient evidence because TeamRater can produce fractional
internal values that are not integer quarter-step indices, and the repository does not
contain a code path establishing the offset.

Zero-based candidate:

```text
internal 21 -> 5.25
```

One-based candidate:

```text
internal 21 -> 5.00
```

The off-by-one difference changes every boundary. The repository contains no evidence
selecting either relationship. No arbitrary offset was introduced.

## Evidence Against Direct Equivalence

- `POSITION_COEFFICIENTS` are decimal weights, not quarter-step lookup tables.
- `PlayerPerformance` modifies skills by a continuous form factor.
- `ContributionCalculator` rounds weighted contributions to two decimals.
- `TeamCalculator` adds contribution values.
- Existing tests assert values such as `11.2` for a single winger's left attack.
- `FormationAnalyzer` sums internal sector totals directly.
- No audited code path maps internal values to Hattrick descriptive levels.
- No audited code path applies Hattrick quarter-step rounding to TeamRater outputs.
- No full-context real-match fixture exists for the user's own lineup with official
  Hattrick ratings for the same lineup, form, stamina, attitude, home/away and tactic.

## Evidence For Hattrick Decimal Imports

- The opponent clipboard parser extracts the numeric cell and stores it as a float.
- Existing opponent calibration tests preserve decimal values and indirect ratings.
- Decimal values at `.00`, `.25`, `.50` and `.75` map cleanly to descriptive sublevels.

This validates imported opponent decimal semantics. It does not validate conversion of
HT Coach internal team values.

## Canonical Rating Types

`engine/ratings/rating_alignment.py` introduces:

- `SectorRatingSource`
- `InternalSectorContribution`
- `HattrickQuarterStepRating`
- `HattrickDecimalRating`
- `ComparableSectorRating`
- `RatingAlignmentFixture`
- `RatingDiagnosticRow`

The types make source identity explicit and prevent plain floats from silently crossing
scale boundaries.

## Developer Diagnostics

`diagnostic_rows_from_ratings(ratings)` returns per-sector diagnostic rows with:

- sector;
- raw internal value;
- raw type;
- source scale;
- conversion path;
- decimal result when available;
- descriptive label;
- rounding action;
- comparison eligibility.

For current TeamRater values, conversion path is `conversion_unsupported`, decimal result
is empty and comparison eligibility is `not_directly_comparable`.

## Indirect Ratings

Opponent imports may include `indirect_defense` and `indirect_attack`. The current
TeamRater pipeline does not calculate own indirect set-piece sector ratings. The app
must preserve imported opponent indirect values, show our value as unavailable where
needed, and not manufacture an estimate.

## Optimizer Separation

Internal contribution totals remain optimizer inputs and ranking signals. Even if a
future exact or estimated Hattrick decimal representation is introduced, optimizer
precision must remain separate from presentation values.

This sprint does not change:

- TeamRater;
- LineupOptimizer;
- FormationOptimizer;
- FormationAnalyzer;
- expected-goals formulas;
- probability formulas;
- Decision Lab scoring;
- Tactical Advisor rules.

## Final Classification

Classification: **C**.

Meaning:

The current code and fixtures do not prove an exact deterministic relationship between
HT Coach internal sector contribution totals and Hattrick decimal ratings.

Outcome:

- Keep scales not directly comparable.
- Do not introduce a conversion adapter for internal values.
- Preserve Match Intelligence safety behavior.
- Preserve Opponent Rating Calibration source labels.
- Keep collecting full-context own-team fixtures for a later estimator or model
  calibration sprint.

## Recommended Next Action

Alpha 0.5.6.1 should be **Historical Fixture Collection and Rating Estimator Research**.

Collect fixtures containing:

- exact lineup and positions;
- individual orders and order sides;
- official Hattrick sector ratings;
- player form, stamina, experience and availability at match time;
- home/away;
- team attitude and tactic;
- substitutions, red cards and special context where known.

Separate representation equivalence from historical match reproduction. Missing match
context must not be treated as a formula defect.

## Alpha 0.5.8 Midfield Estimator

Alpha 0.5.8 introduces `engine/hattrick_ratings/midfield` as a separate estimator for
own-team midfield. This does not change the final classification above. TeamRater and
optimizer values remain Classification C internal additive contribution totals.

The midfield estimator predicts Hattrick quarter-step units directly from lineup
players, position, order, form, stamina and optional team context. It does not derive
its output from TeamRater midfield by applying a coefficient or offset. Its output is
therefore an independent prediction with explicit confidence and warnings, not proof
that existing internal values are Hattrick decimal ratings.
