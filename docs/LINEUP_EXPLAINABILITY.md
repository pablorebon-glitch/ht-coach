# Lineup Explainability

Alpha 0.6.10 adds a deterministic explanation layer for lineup decisions.

## Question answered

The layer is designed to answer:

> Why is this XI better against this opponent?

It can also answer the inverse question:

> Why not the strongest alternative?

## Data used

Explanations are generated from calculated objective traces and head-to-head
deltas:

- sector changes
- possession/chance-share change
- expected goals change
- opponent expected goals change
- tactic route weights
- training difference
- confidence label

The explanation text is derived from those values. It is not a canned player
exception and does not hardcode player names.

## La Rocha fixture

The permanent regression fixture uses:

- opponent midfield 5.75
- opponent defense 7.50 / 13.00 / 8.50
- opponent attack 4.25 / 7.00 / 4.00
- tactic Attack on Wings

Candidate A:

- defense 4.25 / 5.25 / 4.25
- midfield 6.75
- attack 9.50 / 12.50 / 9.25

Candidate B:

- defense 4.25 / 5.25 / 4.50
- midfield 7.75
- attack 9.25 / 12.25 / 9.00

Using the canonical evaluator, Candidate B is preferred because the midfield
gain and lower concession risk are worth more than the small attack sacrifice in
this matchup. The training impact is zero in the fixture.

## Decision Lab integration

Decision Lab can now carry a `lineup_decision` payload. The payload stores only
serializable view-model data:

- recommended objective trace
- strongest alternative objective trace when available
- future head-to-head comparison details

The normal Match UI is not required to show every diagnostic field. Detailed
candidate traces are intended for diagnostics and future what-if/Decision Lab
surfaces.

## Confidence

Explanation confidence should reflect data quality:

- High: official opponent ratings and validated own ratings.
- Medium: recent but not exact opponent data.
- Low: estimated or scaled data.

The current engine API defaults explicit calibration fixtures to high confidence.
Future official-history integration should pass richer provenance instead of
inferring certainty from numbers alone.
