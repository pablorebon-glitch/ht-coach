# Optimizer Objective

HT Coach Alpha 0.6.10 makes the lineup objective explicit without replacing the
canonical match engine.

## Source of truth

The objective uses the existing pipeline:

- `TeamRater` calculates sector ratings from the XI and individual orders.
- `TacticOptimizer` and `TacticEngine` apply tactic effects where a lineup is
  available.
- `MatchEvaluator` calculates possession, chance share, conversions, expected
  goals and opponent expected goals.
- `ResultProbabilityEvaluator` calculates win/draw/loss probabilities.

No PRE/POST parser, official-rating parser, probability formula, TeamRater
coefficient, tactic formula or optimizer math was replaced in this sprint.

## Objective components

Each evaluated XI can now produce a serializable `LineupObjectiveTrace` with:

- `candidate_id`
- lineup slot summary
- sector ratings
- opponent ratings
- tactic and route weights
- lineup positional score
- possession/chance-share component
- attacking matchup component
- defensive matchup component
- expected goals and opponent expected goals
- win/draw/loss probabilities
- training component
- availability component
- final objective score

For normal tactical optimization, `final_objective_score` is the canonical win
probability. Training is represented separately and is only used by the
head-to-head comparator as a tiebreaker when tactical value is within tolerance.

## Marginal value

The new `HeadToHeadLineupComparator` compares two complete XIs or two complete
rating states against the same opponent. It does not rank a player by isolated
positional score. It evaluates what the changed XI does to:

- midfield control and expected chance share
- offensive route value against the opponent defense
- defensive risk against the opponent attack
- expected scoring impact
- expected concession impact
- training impact

This makes the La Rocha calibration case explicit: the Bassedas variant gains
midfield and right defense, loses a small amount of attack, and the canonical
match evaluator values the midfield/defensive improvement more highly against
that opponent.

## Tactical and training hierarchy

The comparator uses a two-stage preference rule:

1. If the tactical score gap is larger than `TACTICAL_TIE_TOLERANCE`, choose the
   tactically stronger XI.
2. If the tactical gap is within tolerance, use training as a secondary
   tiebreaker.

This preserves the product policy that training can decide close calls but must
not silently override a clearly stronger match-winning XI.

## Pareto frontier

The objective module can select a compact frontier from evaluated traces:

- best possession option
- best attacking-output option
- safest defensive option
- best overall objective option

The frontier is intentionally small and deterministic. It is available for
diagnostics and future Decision Lab UI, but the sprint does not expose a large
raw candidate list in the normal interface.

## Limitations

The objective currently explains the engine's existing expected-goals and
probability outputs. It does not perform outcome machine learning, does not tune
ratings from official POST data, and does not claim false precision beyond the
existing model.
