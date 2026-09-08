# UX Responsibility Model

This document is the single source of truth for which module owns which
responsibility in HT Coach. It exists so future sprints don't reintroduce a second
CSV picker, a History screen that reruns the optimizer, or a Weekly Planner that
quietly starts making its own tactical decisions.

## The model

### Squad

- Is the single place where the roster CSV is loaded.
- Owns the active roster.
- Exposes roster data (and the shared "recent CSVs" list) to the rest of the
  application via the shared workspace settings file.
- Hosts Squad Intelligence (Alpha 0.5.9.1) — a deterministic, evidenced
  per-player classification (role, management status, dimensions, strengths,
  risks, milestone) shown when a player is selected. It reads the active
  training context and the app's existing positional ranking; it does not
  optimize match formations and does not make club-wide financial decisions —
  those remain Match's and a future Club Advisor's job respectively.

### Match

- Is the only module responsible for optimizing formations and individual orders.
- Analyzes the opponent.
- Produces the recommended XI for a given match (League, Cup or Friendly).
- Owns the editable Formation Board. Local board edits are slot-authoritative:
  players may move, but each tactical slot keeps its own valid order intent unless
  that slot's assignment makes the order invalid.
- Keeps Match workspace controls responsive in restored and maximized windows; the
  Formation Board header may use multiple compact rows so primary actions remain
  reachable without shrinking the pitch.
- Treats mouse-wheel input as page scrolling, not as selector editing. Closed
  Match combos, Formation Board order/tactic/attitude/formation selectors and
  Match result tabs change only through deliberate click or keyboard actions.
- Imports the official Hattrick Match Summary associated with the match (Alpha
  0.5.9.0 / UX-02) — parsing and attaching it never reruns the optimizer or any
  rating formula; the imported values are stored exactly as Hattrick provided them.
- Uses competition type as product intent: League and Cup are competitive after
  training feasibility, while Friendly rotates away from Match 1 starters when
  valid alternatives exist.
- Remains focused on the selected match - it does not manage training priorities
  or long-term squad development.

### Weekly Training Planner

- Displays the week's two matches (first match, second match).
- Shows which players receive training and how much.
- Calculates weekly training coverage.
- Assigns and maintains player training priorities.
- Does **not** independently optimize a match lineup - the competition-aware
  lineup is produced by Match. Weekly Planner supplies which players are still
  owed training minutes and, for Friendly rotation, the canonical Match 1 lineup
  from the same training cycle.
- Does not replace Match as the source of tactical decisions.

### History (`engine/history`, `engine/history/evolution`, `engine/history/insights`)

- Stores historical snapshots (Alpha 0.5.8.2).
- Compares equivalent matches deterministically (Alpha 0.5.8.3 — Evolution Engine).
- Explains deterministic changes with evidenced, confidence-scored insights (Alpha
  0.5.8.4 — Insights Engine).
- Must never rerun the optimizer merely to display historical data. Historical
  lineups, orders and ratings are read directly from the canonical persisted
  snapshot — never recomputed. This is enforced by
  `tests/test_history_responsibility_boundaries.py`, which statically scans the
  `engine/history/evolution` and `engine/history/insights` packages for any import
  of `FormationOptimizer`, `LineupOptimizer`, `TacticOptimizer` or `OrderOptimizer`,
  and behaviorally confirms insight generation succeeds from snapshots alone.

## Hard rules

- **Do not let retrospective PRE evidence rename a match.** History owns the
  canonical opponent/date/competition/venue/Match ID. Retrospective source
  opponent and source Match ID remain provenance only, and visible match titles
  are generated from canonical structured fields.
- **Do not save historical weekly matches into the current week by default.**
  Match must use the record's own scheduled date to choose the Sunday-Saturday
  training cycle. Missing dates require user correction instead of guessing.
- **Do not add a second CSV-loading workflow.** Match, Weekly Planner and History
  all consume the roster/CSV that Squad already owns; none of them get their own
  "Browse/Load" pair. Match's players-CSV control is a "recent files" picker, not an
  independent load path.
- **Do not run Match analysis from History.** A historical snapshot's lineup and
  ratings are fixed at the moment they were saved. Comparing or explaining them
  never triggers a new optimization.
- **Do not let Weekly Planner make tactical decisions.** It surfaces priorities and
  coverage; Match decides how to satisfy them against a specific opponent.
- **Do not bind tactical changes to hover-wheel input.** Wheel scrolling is page
  navigation unless the user explicitly opened a popup or is inside a real
  scrollable content area.

## Why this exists

Earlier in the project's history, CSV loading, roster ownership and lineup
optimization drifted across modules in ways that were easy to reintroduce by
accident (e.g. a second file picker on the Match page, or a "generate plan" button
inside the Planner that silently duplicated Match's optimizer). Alpha UX-01
established the model above; every history-related sprint since (0.5.8.2, 0.5.8.3,
0.5.8.4) has treated it as a guardrail rather than a suggestion; this document exists
so it stays that way.
