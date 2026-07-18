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
