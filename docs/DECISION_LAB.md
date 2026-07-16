# HT Coach Decision Lab

## Purpose

Decision Lab explains why HT Coach recommends a formation, what trade-offs the choice
creates, and how it compares with analyzed alternatives.

It is an interpretation layer over existing Match analysis results. It does not change
ratings, formations, optimizers, tactic behavior, probability calculations, or expected
goal formulas.

## Inputs

Decision Lab consumes serializable Match analysis view-model data:

- formation name;
- tactic and tactic level;
- win, draw and loss probabilities;
- possession;
- expected goals and opponent expected goals;
- team and opponent sector ratings;
- lineup and individual orders;
- baseline, best-normal, best-order and final win probabilities;
- lineup, order, tactic and total gains.

## Rules And Thresholds

Rules are centralized in `ht_coach_app.reasoning.comparison_analyzer`.

Initial interpretation bands:

- negligible win gap: under 0.25 percentage points;
- small win gap: 0.25 to 1.0 points;
- meaningful win gap: 1.0 to 3.0 points;
- strong win gap: over 3.0 points;
- meaningful xG gap: 0.15 xG;
- meaningful possession gap: 1.5 percentage points;
- slight sector gap: 5 percent relative difference;
- strong sector gap: 15 percent relative difference.

xG interpretation bands:

- below 0.80: low;
- 0.80 to below 1.20: moderate;
- 1.20 to below 1.70: dangerous;
- 1.70 or higher: very dangerous.

Optimization-gain display:

- hide individual gains below 0.05 percentage points;
- display visible gains as Better XI, Individual orders, Team tactic and Total
  improvement;
- avoid `+0.0 pp` and negative zero in user-facing text.

## Confidence

Confidence is deterministic and uses:

- win-probability gap between first and second formation;
- number of formations analyzed;
- whether metrics point in the same direction;
- whether the recommendation is effectively tied with alternatives;
- whether a specialized tactic gain is negligible.

Confidence levels are `HIGH`, `MEDIUM`, and `LOW`. They describe confidence in the
recommendation relative to the analyzed alternatives, not certainty about the real match.

## Sector Matchups

Decision Lab compares:

- our left attack vs opponent right defense;
- our central attack vs opponent central defense;
- our right attack vs opponent left defense;
- opponent left attack vs our right defense;
- opponent central attack vs our central defense;
- opponent right attack vs our left defense.

Classifications:

- Strong advantage;
- Slight advantage;
- Balanced;
- Slight disadvantage;
- Strong disadvantage.

These labels are explanations of rating gaps only. They do not create new probabilities.

Decision Lab never labels a disadvantage as a best attacking advantage. If all attacking
channels are balanced, it says there is no clear attacking channel advantage. If all
channels are unfavorable, it says no attacking advantage was detected and may identify
the least unfavorable channel.

## Tactic Observations

Tactic observations describe behavior already represented by the engine:

- Normal;
- Attack in the Middle;
- Attack on Wings;
- Pressing;
- Counter-Attacks;
- Play Creatively;
- Long Shots.

The observation also explains why the tactic was selected in this analysis by using the
stored tactic gain. If that gain is negligible, the wording explicitly says the
improvement is marginal.

## Persistence

Decision Lab results are persisted as serializable view-model data inside the last Match
analysis result. Older saved results without reasoning data are restored safely and can
regenerate reasoning from stored formation rows when possible. Malformed reasoning data
falls back without crashing the application.

## Limitations

- Explanations are deterministic and rule-based.
- No AI service, LLM, network dependency, or external API is used.
- Decision Lab does not guarantee match outcomes.
- Reasoning quality depends on the formations and opponent data analyzed by the user.

## Example

`3-5-2` may be recommended because it has a meaningful win-probability edge, creates more
xG, and keeps opponent xG in a similar range. The same result may still flag a wing
defensive vulnerability when opponent attack ratings exceed our defensive sector rating.
