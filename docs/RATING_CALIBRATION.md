# Rating Calibration

HT Coach uses a dedicated rating normalization layer to convert raw internal
lineup ratings into HT-compatible estimates before matchup calculations.

## Canonical Target

The canonical analytical target is `HT_CALIBRATED_ESTIMATE`, compatible with
official Hattrick decimal ratings. This keeps opponent imports, PRE/POST
evidence and user-facing explanations on the same scale.

## Bootstrap v1

Current version: `internal-to-ht-bootstrap-v1`.

Bootstrap v1 is a low-confidence sector-specific mapping derived from the
confirmed La Rocha scale audit baseline and the official-scale Candidate B
reference. It is intentionally replaceable and exposes its confidence, sample
count and derivation.

It is not a magic global divisor. Each sector has its own slope.

## Historical Rebuild

`rebuild_rating_calibration(history)` builds samples from historical records
where an internal prediction and Official PRE snapshot exist for the same match.
POST snapshots are kept as secondary evidence and are not pooled into the PRE
fit because substitutions, events and stamina can change the final rating.

If the sample count is too small, HT Coach falls back to Bootstrap v1.

## Storage

Desktop persistence stores the calibration model in application data as
`rating_calibration.json`. Portable mode stores it under the portable data
directory. Match Records keep their own evidence unchanged; analyses record the
calibration version used.

## Limitations

Bootstrap v1 is low confidence. More real Official PRE pairs are required before
the mapping can be considered calibrated. Outcome results and scorelines are not
used to fit rating scale.
