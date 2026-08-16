# Match Calibration Evidence

Alpha 0.6.12 distinguishes calibration evidence by role instead of treating all
official data as interchangeable.

## Evidence Types

- `PRE_RATING_PAIR`: internal HT Coach prediction vs Official PRE. This remains
  the primary source for internal-to-HT rating calibration.
- `POST_VALIDATION_PAIR`: internal HT Coach prediction vs Official POST. This is
  secondary validation evidence because substitutions, events and stamina can
  affect final ratings.
- `OPPONENT_SCENARIO_PAIR`: expected opponent scenario vs actual opponent POST
  from a bilateral import. This measures scenario drift and future opponent
  model quality; it does not train probability or xG formulas.

Each sample stores stable identity fields: match record id, official match id,
sector, values, source, confidence, timestamp and calibration version where
available.

## Calibration Hierarchy

The Alpha 0.6.11 normalization model is unchanged. `rebuild_rating_calibration`
continues to fit from Official PRE pairs only and falls back to Bootstrap v1 when
sample volume is too small.

Bilateral POST is historical evidence for validation and future research, not a
replacement for PRE-based calibration.

## Scenario Drift

`engine.history.official_ratings.scenario_drift` compares an expected opponent
snapshot with the actual opponent POST side when both exist. It reports sector
deltas, tactic/style changes where present, and a typed magnitude:

- `NONE`;
- `LOW`;
- `MEDIUM`;
- `HIGH`;
- `UNKNOWN`.

Scoreline is stored as historical metadata, but it is not used to classify drift
or calibrate rating scale.
