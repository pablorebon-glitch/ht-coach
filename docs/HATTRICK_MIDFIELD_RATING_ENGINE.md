# Hattrick Midfield Rating Engine v1

Alpha 0.5.8 introduces an independent own-team midfield estimator in
`engine/hattrick_ratings/midfield`.

## Separation

HT Coach now has two distinct concepts:

- internal lineup strength, used by the existing optimizer;
- predicted Hattrick rating, used to estimate a displayed Hattrick sector rating.

Midfield Rating Engine v1 does not call TeamRater, FormationAnalyzer,
ContributionCalculator, LineupOptimizer, FormationOptimizer, Decision Lab, Match
Intelligence, probability or expected-goals code. It does not convert internal
contribution totals with offsets or coefficients.

## Rating Representation

`HattrickRating` stores `quarter_steps: int` as the canonical value. Decimal display is
derived from quarter steps:

```text
quarter_steps 21 -> 5.25 HT
```

Named level/sublevel display reuses the existing Hattrick mapping from the rating
alignment audit. If a level is missing, decimal display remains canonical.

## Input

`MidfieldRatingInput` contains:

- lineup;
- formation label;
- `MidfieldRatingContext`.

Context supports:

- `MatchPeriod.START`;
- `MatchPeriod.END`;
- team spirit when known;
- Normal, Play It Cool and Match of the Season attitudes;
- coach string for future calibration metadata.

Qt is not imported by this engine.

## Supported Positions

Supported midfield contribution positions in v1:

- Inner Midfielder;
- Winger;
- Wing Back;
- Central Defender;
- Forward;
- Goalkeeper with zero midfield weight.

Goalkeeper is explicitly modeled as zero midfield contribution in v1 rather than
silently omitted.

## Supported Orders

Supported order effects are parameterized by position:

- Inner Midfielder: Normal, Offensive, Defensive, Towards Wing;
- Winger: Normal, Towards Middle, Offensive, Defensive;
- Wing Back: Normal, Towards Middle, Defensive, Offensive;
- Central Defender: Normal, Offensive, Defensive;
- Forward: Normal, Defensive, Offensive, Towards Wing;
- Goalkeeper: Normal.

Unsupported position/order combinations fall back to a neutral order modifier and emit
`unsupported_order` in the structured breakdown.

## Formula And Parameters

The v1 formula is parameterized in `MidfieldModelParameters`.

```text
player contribution =
  playmaking
  * position weight
  * order modifier
  * form modifier
  * stamina modifier

raw rating =
  base rating
  + sum(player contribution) / playmaking scale
  * team context modifiers

rounded rating =
  nearest Hattrick quarter step
```

These are v1 estimator parameters, not a claim of exact Hattrick formula replication.
They are intentionally centralized so later calibration can update the model under a
new version.

## Form

Form uses a dedicated curve around neutral form 7. Missing form applies a conservative
modifier and emits `missing_form_assumed`.

## Stamina

The engine supports start and end estimates. Start uses no stamina penalty. End applies
a conservative stamina curve; missing stamina emits `missing_stamina_assumed`.

Minute-by-minute accuracy is not claimed.

## Team Context

If team spirit is missing, v1 assumes neutral team spirit and emits
`neutral_team_spirit_assumed`.

If attitude is unknown, v1 assumes Normal and emits `unknown_attitude_assumed_normal`.

Coach details are recorded only as context. Missing coach metadata emits
`missing_coach_context`; it does not currently change the rating.

## Confidence

Every prediction includes confidence. Because v1 is not calibrated against a complete
real-match dataset, default predictions include `model_uncalibrated` and return
`UNCALIBRATED` confidence.

## Breakdown

The prediction includes structured data:

- player contribution by player;
- position and order;
- playmaking component;
- form modifier;
- stamina modifier;
- context modifiers;
- warning codes;
- raw rating;
- final quarter-step rounding.

The engine stores codes and parameters, not localized prose.

## Validation

`MidfieldRatingPredictionProvider` integrates with `engine/rating_validation`.

Validation fixtures may include `additional_context.lineup_players` and
`additional_context.midfield_context`. The provider predicts only midfield and leaves
all other sectors empty.

CLI:

```powershell
.\.venv\Scripts\python.exe -m engine.hattrick_ratings.midfield.calibration fixtures\hattrick\midfield_v1_reference.json
```

Metrics include exact quarter-step accuracy, within 0.25, within 0.50, mean absolute
error, median absolute error, signed bias, maximum error and sample count.

Alpha 0.5.8.1 adds `engine/hattrick_ratings/calibration`, a real-match calibration
dataset workflow for `midfield-v1`. It records played-match lineup snapshots, official
Hattrick midfield ratings, validation quality and model-versioned observations. The
workflow can recalculate error reports and export/import validation fixtures, but it
does not tune parameters or change the `midfield-v1` formula.

CLI:

```powershell
.\.venv\Scripts\python.exe -m engine.hattrick_ratings.calibration --store .ht_coach_calibration\real_match_records.json report --model midfield-v1
```

See `docs/REAL_MATCH_CALIBRATION.md` for the full record schema and workflow.

## Opponent Comparison

When own predicted midfield and opponent midfield are both on the Hattrick decimal
scale, `compare_midfield_rating()` can classify the relationship as `lower`, `similar`
or `higher`. It does not calculate possession, win probability or expected goals.

## UI Integration

Desktop UI integration is explicitly deferred in Alpha 0.5.8 because current Match
accordion/responsive work is being stabilized. The engine is exposed through tests,
fixtures and CLI/report integration first. A later UI milestone can add a compact,
localized read-only display without changing the engine.

## Known Limitations

- Midfield only.
- Dataset capture exists, but `midfield-v1` is not yet tuned from a complete real-match
  dataset.
- No defense or attack predictions.
- No possession, win probability or expected-goals prediction.
- No automatic Hattrick scraping.
- No claim of exact official Hattrick formula replication.

## Future Work

- Add complete real-match fixtures.
- Calibrate parameters under a new model version.
- Add defense and attack engines.
- Add compact UI display once Match layout work is settled.
