# HT Coach Product Vision

HT Coach helps a Hattrick manager prepare a match quickly, understand the recommendation,
and keep enough detail available for deeper review.

## Product Pillars

### 1. Calculate

Find the strongest lineup, formation, individual orders and tactic using the stable
optimization engine.

### 2. Explain

Explain why the recommendation is preferred. The manager should understand the main
trade-off instead of only seeing raw probabilities.

### 3. Visualize

Present the recommendation in a natural football context. The lineup should be readable
as a pitch before it is read as a table.

### 4. Experiment

Eventually allow the manager to test changes and see their impact without losing the
optimized recommendation as the baseline.

## Principles

- Every recommendation must be explainable.
- The engine calculates; the UI interprets and visualizes.
- Do not alter engine output to improve presentation.
- Every interaction should move the manager closer to a decision.
- A manager should be able to prepare a match in under five minutes.
- Prefer conclusions over raw numbers where appropriate.
- Preserve access to detailed numbers for advanced users.

## Alpha 0.4 Sequence

- 0.4.1 Formation Viewer
- 0.4.2 Player Intelligence
- 0.4.3 Editable Lineup Board
- 0.4.4 Drag and Drop
- 0.4.5 One-Click Workspace
- 0.4.6 What-if Evaluation and Decision Delta

Alpha 0.4 starts with a read-only Formation Viewer and deterministic Player
Intelligence, then adds immediate workspace editing before broader what-if evaluation.
These milestones preserve the stable optimization engine.

## Product Principles (Alpha 0.5.8.5)

As HT Coach grew from a single Match-analysis tool into four cooperating modules
(Squad, Match, Weekly Training, History), the following principles keep that growth
coherent rather than accidental:

1. **Hattrick is the source of truth.** HT Coach never invents facts Hattrick
   itself hasn't provided — no estimated official ratings, no fabricated match
   results, no guessed skill values.
2. **HT Coach supports decisions; it does not replace the game.** The manager
   remains the decision-maker for every trade-off the app surfaces.
3. **Squad owns the roster.** It is the only place the roster CSV is loaded, and
   the only source of truth for who is currently on the team. See
   docs/UX_RESPONSIBILITY_MODEL.md for the full boundary.
4. **Match owns lineup optimization.** It is the only module that produces a
   recommended XI, formation, individual orders or tactic.
5. **Training evaluates coverage and priorities.** It tracks who trains, under
   which of the (now twelve) senior training types, and whether prioritized
   players are covered — it does not compete with Match to pick a lineup.
6. **History records official and contextual information.** Snapshots, their
   deterministic evolution and their evidenced insights are all read-only replays
   of what already happened — History never reruns an optimizer to produce or
   alter historical data.
7. **Advisor-style functionality must explain its reasoning.** Every
   recommendation, insight or trade-off the app surfaces should be traceable to
   specific evidence, not an opaque score. Causal language is treated carefully:
   an observed correlation is never presented as a proven cause (see
   docs/ARCHITECTURE.md's Historical Insights Engine section for how this is
   enforced in code, not just in wording).
8. **Recommendations are contextual to the club's strategy.** A recommendation
   that's right for a club chasing an immediate promotion may not be right for one
   rebuilding for next season; features should leave room for that context even
   before the club expresses it explicitly.
9. **Current reference strategy is sustainable growth.** Until a club can set its
   own strategy (a future Club Advisor concern), HT Coach's defaults assume the
   manager wants steady, sustainable squad development rather than short-term
   sporting risk-taking or financial speculation.
10. **Every feature must answer a concrete manager decision.** "Which second-match
    lineup covers my training priorities without losing too much sporting
    strength?", "Did my midfield actually improve, and why?", "Which of my
    prioritized players are covered this week?" — if a proposed feature can't be
    phrased as a decision a manager is trying to make, it doesn't belong in this
    version of the product.

### Explicitly future, not configurable today

**Club DNA** (a club-level configurable strategy profile influencing
recommendations across Match, Training and a future Club Advisor) is a real,
anticipated future extension — but it is not implemented, and no sprint before
Alpha 0.6.0 should attempt a partial version of it. Until then, "sustainable
growth" (principle 9) is the single implicit reference strategy.

## Understanding Every Player (Alpha 0.5.9.1)

Principles 1 and 10 ("Hattrick is the source of truth" / "every feature must
answer a concrete manager decision") became concrete for individual players with
Squad Intelligence: for any current-roster player, HT Coach now answers, within
five seconds and with evidence — not an opaque score — who they are within the
sporting project, what to currently do with them, and why.

This is deliberately still a *reporting* layer, not a decision-maker: recommended
roles and management statuses (KEEP, TRAIN, MONITOR, EVALUATE_SALE, and so on)
are inputs to the manager's own judgment, evaluated against the single reference
strategy this sprint implements — sustainable growth — represented as a typed,
swappable input rather than hardcoded, so a future club-strategy sprint can
extend it without redesigning anything. There is deliberately no unconditional
"sell" status yet: HT Coach doesn't know club finances, market prices or transfer
deadlines, so it says "evaluate," not "sell."

## Official Ratings Are the Truth (Alpha 0.5.9.0)

Principle 1 ("Hattrick is the source of truth") became concrete with Alpha 0.5.9.0:
HT Coach can now import Hattrick's own official ratings via the "Copy Ratings"
workflow (see docs/OFFICIAL_RATING_WORKFLOW.md), and once imported, those values are
authoritative:

> HT Coach proposes. Hattrick calculates. HT Coach learns.

HT Coach's own predicted ratings remain a genuinely useful estimate produced *before*
the game calculates anything — that's what makes lineup optimization possible in the
first place. But once Hattrick has actually calculated the official ratings for a
match (before or after it's played), HT Coach:

- **Compares** its own prediction against the official values, sector by sector.
- **Learns** from the gap, over time, which is diagnostic information for a future
  Decision Validation sprint — not something presented as the primary Match UI.
- **Explains** any pattern it finds, following the same evidence-and-confidence
  discipline as the Historical Insights Engine.
- **Advises** based on that learning, once a future Advisor exists to do so.

It **never overwrites** an official value with its own recalculation. This is the
same discipline History has followed since Alpha 0.5.8.2 (never rerun the optimizer
to produce historical data) applied to a new kind of data: once something Hattrick
itself calculated is on record, HT Coach's job is to learn from it, not replace it.

UX-02 made this workflow actually reachable from the app (a single "Import Official
Match Summary" action in Match) rather than an engine capability with no door into
it — the same "propose, don't replace" discipline extends to how it's presented:
when HT Coach's own predicted ratings and an imported official value are shown
together, and the two scales aren't yet confirmed to align, HT Coach says so
plainly instead of showing a number that implies more precision than it has.
