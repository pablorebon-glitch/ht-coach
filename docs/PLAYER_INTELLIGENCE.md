# Player Intelligence

Alpha 0.4.2 upgrades the Formation Viewer inspector into a deterministic Player
Intelligence panel. It explains the selected player before showing raw attributes.

## Purpose

Player Intelligence answers:

- what kind of player this is;
- why the player was selected;
- what the player contributes tactically;
- what limitations or risks exist;
- which players are the closest alternatives;
- why those alternatives were not selected.

It is read-only. It does not edit the lineup, swap players, rerun optimization, or
calculate what-if match deltas.

## Architecture

```text
FormationBoard
  -> PlayerIntelligenceService
  -> immutable PlayerIntelligenceViewModel
  -> existing roster data
  -> existing PlayerAnalyzer / ContributionCalculator
```

The `ht_coach_app/player_intelligence/` package is UI-independent and does not import
Qt. Widgets only render view models returned by this application layer.

## Deterministic Rule System

Rules are centralized in:

- `profile_classifier.py`
- `explanation_rules.py`
- `alternative_analyzer.py`
- `contribution_formatter.py`

The rules use existing player attributes, the current assignment, existing
`PlayerAnalyzer` ranking, and existing contribution calculation. They do not introduce
AI, LLMs, network calls, hidden traits, chemistry, or unsupported game mechanics.

## Player Profile Classification

Profiles are modest presentation summaries, not engine mechanics.

Examples:

- Goalkeeper: Shot Stopper, Experienced Goalkeeper, Developing Goalkeeper.
- Central Defender: Defensive Anchor, Ball-Playing Defender, Balanced Defender.
- Wing Back: Defensive Fullback, Attacking Wing Back, Balanced Wing Back.
- Inner Midfielder: Playmaker, Defensive Midfielder, Creative Midfielder,
  Box-to-Box Midfielder, Balanced Midfielder.
- Winger: Creative Winger, Attacking Winger, Defensive Winger, Balanced Winger.
- Forward: Primary Finisher, Creative Forward, Complete Forward, Support Forward.

Thresholds compare visible skills such as scoring, passing, playmaking, defending,
winger, goalkeeper and experience. Labels avoid exaggerated terms such as elite.

## Strengths And Limitations

Strengths and limitations are generated from relevant role skills, form, stamina and
whether the current assignment is the player's strongest evaluated position.

The panel limits each list to the most useful points. Neutral players do not receive
forced criticism.

## Why Selected

When roster data is available, the service ranks candidates for the same current
position and side using existing `PlayerAnalyzer.rank_players`.

Wording is careful:

- if the player ranks first, the panel can say highest evaluated player for this role;
- if data is incomplete, it says selected by the optimizer for this analyzed lineup;
- if alternatives are close, it explicitly treats them as credible replacements.

The service never claims a player is best in the squad unless the same-role ranking
supports it.

## Tactical Contribution Visualization

Contribution bars use existing `ContributionCalculator` values grouped into
role-relevant categories. Bars are normalized against the maximum relevant roster value
for that category.

Bars are visualized player-score/contribution profiles. They are not match probabilities
and do not imply win-probability changes.

## Alternative Ranking

Alternatives are ranked with the same current position and side. The selected player is
excluded. Up to three alternatives are shown.

Each alternative displays:

- player name;
- positional score;
- player score difference;
- one or two comparison points;
- why the alternative was not selected.

Score deltas are explicitly player-score differences, not win-probability deltas.

## Effective-Tie Thresholds

- Effective tie: absolute player-score difference below `0.25`.
- Competitive alternative: absolute player-score difference below `1.0`.
- Larger gaps are described as clearer role downgrades or, if the alternative rates
  higher, as higher-rated but not part of the analyzed optimized XI.

These thresholds are explanation thresholds only. They do not change engine behavior.

## Missing-Data Behavior

Persisted or restored match results may not have roster details available. In that case:

- the pitch still renders;
- player selection shows a clean unavailable state;
- no exception is raised;
- the panel avoids partial or misleading explanations.

## Compact Inspector Layout

Alpha 0.4.2.1 keeps the coach note, why-selected rationale, strengths, limitations,
tactical contributions and alternatives in a denser inspector beside the pitch.
Technical Details starts collapsed. The inspector owns its vertical scroll area, so
overflow does not create a Match-page scrollbar or reduce the full-pitch view. These are
presentation changes only; profile rules, explanations, contribution values and
alternative rankings are unchanged.

## Performance Constraints

Player selection must remain lightweight. Player Intelligence uses loaded roster data,
serialized lineup data, and existing player rating/contribution helpers. It does not
call:

- `FormationOptimizer`;
- `LineupOptimizer`;
- `OrderOptimizer`;
- `TacticOptimizer`;
- full match analysis.

## Explicit Non-Mechanics

HT Coach does not implement player chemistry, hidden player relationships, invented
traits, or unsupported tactical effects. Hattrick does not have FIFA-style chemistry, so
the UI must not imply it.

## Future Use

Player Intelligence prepares the explanation layer for later editable lineup and
Decision Delta work. Future what-if features can compare manual changes against the
optimized recommendation without changing this milestone's read-only guardrails.
