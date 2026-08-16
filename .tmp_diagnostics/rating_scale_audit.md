# Rating Scale Audit

Players loaded: 18
La Rocha best formation: 2-5-3
La Rocha tactic: Attack on Wings (4.705)
Internal own midfield vs opponent midfield: 39.6800 vs 5.75
xG: 9.551806 - 0.000353
W/D/L: 0.99991429 / 0.00008568 / 0.00000003

First mixed-scale comparison: `MatchEvaluator.evaluate` compares internal `our_ratings.midfield` directly against imported Hattrick-decimal `opponent_ratings.midfield`.

Candidate A official-scale win: 0.587561
Candidate B official-scale win: 0.729629

No production internal-to-Hattrick conversion was found in the optimizer/xG path.