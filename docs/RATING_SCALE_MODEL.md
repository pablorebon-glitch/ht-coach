# Rating Scale Model

## Alpha 0.6.12 Evidence Boundary

Bilateral Official POST enriches historical evidence without changing the rating
scale model. The internal-to-HT mapping remains the Alpha 0.6.11 calibration
layer; POST observations are stored as validation samples and opponent scenario
samples, not as primary calibration coefficients.

HT Coach separates rating prediction from match decision math.

## Scales

`INTERNAL_CONTRIBUTION` is the raw additive output from player, position and order
engines. It is useful for lineup construction and diagnostics, but it is not a
Hattrick sector rating.

`HT_OFFICIAL_DECIMAL` is the official Hattrick decimal rating scale imported from
PRE/POST summaries or entered for opponents.

`HT_CALIBRATED_ESTIMATE` is HT Coach's calibrated estimate of our own lineup on
an HT-compatible scale. Matchup, xG and W/D/L calculations must use this scale
against opponent HT ratings.

`UNKNOWN` is allowed for backward-compatible fixtures and persisted historical
data, but analytical production paths should not rely on it.

## Analytical Contract

`MatchEvaluator.evaluate()` validates scale compatibility before calculating
possession, xG or probabilities. Mixed explicit scales are rejected. The Match
Workspace normalizes own internal ratings to `HT_CALIBRATED_ESTIMATE` and treats
opponent imports as HT-compatible before calling the evaluator.

## Three Layers

Layer 1: rating prediction.
Players, formation and orders produce internal sector totals and then an
HT-compatible estimate.

Layer 2: decision model.
Own HT-compatible ratings and opponent HT ratings produce possession, xG,
opponent xG and W/D/L.

Layer 3: outcome calibration.
Long-term probability accuracy versus real results is separate and is not tuned
by this sprint.

## Guardrail

The old mixed-scale La Rocha diagnostic, where midfield `39.68` was compared
directly with opponent midfield `5.75`, is no longer a valid calibrated
evaluation.
