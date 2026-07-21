# Rating Validation Framework

Alpha 0.5.6.1 adds infrastructure for measuring future rating engines against real
Hattrick match ratings.

This is not a rating engine. It does not predict, convert, calibrate, estimate or tune
ratings. It only stores fixtures, accepts predictions when supplied, compares them
against official ratings and reports error metrics.

## Purpose

Alpha 0.5.6 classified current HT Coach sector values as internal contribution totals
that are not directly comparable with Hattrick decimal ratings.

The next safe step is a validation framework:

- preserve real match fixtures;
- classify fixture completeness;
- keep official ratings separate from predicted ratings;
- measure prediction error objectively;
- report coverage, warnings and ignored fixtures;
- provide a future `RatingPredictionProvider` interface.

## Package

```text
engine/rating_validation/
  __init__.py
  fixture.py
  dataset.py
  validator.py
  metrics.py
  report.py
  loader.py
  exceptions.py
```

The package is independent of Qt and does not import the desktop application.

## Fixture Model

`RatingValidationFixture` contains:

- `fixture_name`;
- `match_id`;
- `team_name`;
- `formation`;
- `orders`;
- `players`;
- `home_or_away`;
- `attitude`;
- `confidence`;
- `coach`;
- `weather`;
- `metadata_complete`;
- `official_hattrick_ratings`;
- `predicted_ratings`;
- `notes`;
- `additional_context`;
- optional explicit `completeness`.

The model is intentionally extensible. Future sprints can add richer lineup, player,
match-event or source metadata without changing the validator contract.

## Rating Models

Official ratings use `OfficialHattrickRatings`.

Predicted ratings use `PredictedRatings`.

Both expose the canonical nine Hattrick sectors:

- midfield;
- right defense;
- central defense;
- left defense;
- right attack;
- central attack;
- left attack;
- indirect defense;
- indirect attack.

Official ratings are authoritative observed values. Predicted ratings are optional
inputs supplied by a future engine or test fixture. The framework never derives
predicted ratings from HT Coach internal contribution values.

## Completeness

Fixtures are classified as:

- `COMPLETE`: official ratings plus complete match context.
- `PARTIAL`: official ratings exist but some match context is missing.
- `MINIMAL`: official ratings are known but match context is effectively absent.
- `UNKNOWN`: insufficient official rating data for meaningful validation.

Validation reports expose completeness for every fixture so future datasets can separate
strong evidence from weak evidence.

## Dataset

`RatingValidationDataset` stores immutable fixture tuples and supports iteration,
counting, filtering, grouping by completeness and duplicate fixture identifier
detection.

The fixture identifier is `match_id` when present, otherwise `fixture_name`.

## Loader

`load_rating_validation_dataset(path)` supports JSON files and JSON directories.

Supported JSON shapes:

```json
{
  "fixtures": [
    { "fixture_name": "fixture_01" }
  ]
}
```

or a single fixture object. YAML is intentionally left for a future loader extension.

## Reference Fixture

`fixtures/hattrick/pata2008_reference.json` stores the Alpha 0.5.6 opponent example as
a proper validation fixture.

It includes official Hattrick decimal ratings and known missing context. It is marked
`minimal` because lineup, players, orders, home/away, attitude, confidence, coach and
weather are not known.

## Validator

`RatingValidator` validates one fixture or a dataset.

Responsibilities:

- skip fixtures without official ratings;
- skip fixtures without predictions unless a provider is supplied;
- compare only sectors where official and predicted values both exist;
- report missing predicted sectors;
- calculate global and per-sector metrics;
- return structured reports without console formatting.

The validator accepts a future `RatingPredictionProvider`, but does not implement one.

## Metrics

Implemented metrics:

- absolute error sum;
- mean absolute error;
- maximum error;
- root mean squared error;
- mean signed error;
- count;
- ignored count;
- comparison count.

Metrics are calculated globally and per sector.

## CLI

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe tools\validate_ratings.py fixtures\hattrick
```

Example output:

```text
Fixtures: 1
Comparable: 0
Ignored: 1
Comparisons: 0
Coverage: 0%
Overall MAE: 0.00
Overall RMSE: 0.00
Worst Fixture: Not available
Warnings:
- pata2008_reference_opponent: missing predicted ratings
```

## Limitations

- No rating prediction is implemented.
- No conversion from HT Coach internal contribution values is implemented.
- No calibration, curve fitting or machine learning is implemented.
- The initial reference fixture is minimal and cannot validate a future rating engine by
  itself.
- Full validation will require complete own-team match fixtures with lineup, orders,
  player state and official Hattrick ratings.
