# Weekly Training Lineup Planner

Alpha 0.5.7 adds a weekly training planner to the Squad page. Alpha 0.5.7.2 adds
the Planner Execution Engine, so the planner now generates an actual second-match
lineup instead of behaving only as a validator. The first supported training type is
Playmaking.

The planner helps answer a practical Hattrick question: after the first match of the
training week, which second-match lineup covers the training priorities while keeping
the team competitive?

## Scope

The optimization engine remains stable. The planner does not change rating formulas,
probability calculations, tactic behavior, order behavior or existing optimizers.

It uses existing roster import, player ranking, formation catalog, Formation Board and
automatic order support. New logic is limited to training-week state, Playmaking
exposure rules, priority persistence, coverage aggregation and constrained lineup
selection.

## Active Week

The default schedule is:

- Sunday: first weekly match.
- Wednesday: second weekly match.
- Thursday: training update.

`active_training_week()` calculates the current training week in the
`America/Buenos_Aires` timezone by default. On or after Thursday, the active planning
window rolls forward to the next Sunday.

The persisted week stores:

- week id;
- Sunday start date;
- Wednesday second-match date;
- Thursday training update date;
- active training type;
- lifecycle status.

## Priority Model

Each player can have one weekly priority. Alpha 0.5.7.1.1 simplifies the visible
UI choices to:

- 100%;
- 50%;
- No priority / Sin prioridad.

Backward-compatible stored values are mapped explicitly:

- Required 100% and High priority display as 100%;
- Required 50% and Secondary priority display as 50%;
- Rest and No priority display as No priority / Sin prioridad.

The persistence model can still read the original values:

- Required 100%;
- Required 50%;
- High priority;
- Secondary priority;
- No priority;
- Rest.

Priorities persist by a deterministic roster identity based on player name, age, days,
TSI and salary. This avoids collapsing duplicated names while preserving importer
compatibility.

## Playmaking Rules

Playmaking exposure is minute-aware:

- Inner Midfielder gives 100% training factor.
- Winger gives 50% training factor.
- Other positions give 0% Playmaking training factor.

When exact played minutes are unavailable, the planner assumes 90 minutes for starters
and marks exposure as assumed rather than confirmed.

## Match Records

Weekly match records are serializable JSON objects containing:

- match id;
- match date;
- weekly role;
- formation;
- lineup entries;
- planned or played status;
- minutes-known flag;
- training exposure entries.

Confirmed played records, assumed played records and planned records remain distinct in
coverage output. Rollover archives the week marker while retaining match records for
history and diagnostics.

## Planner Algorithm

The planner currently supports fixed-formation planning. The Squad UI lets the user
choose any supported formation from the central formation catalog.

Hard constraints:

- unsupported training types are rejected;
- unsupported formations are rejected;
- unavailable or Rest players cannot be selected;
- a legal lineup requires at least one valid goalkeeper;
- every generated lineup must contain eleven unique starters.

Soft objectives:

- place remaining Required 100% and Required 50% targets first;
- prefer High and Secondary targets in trainable slots;
- complete the lineup using the existing player ranking engine;
- apply the existing automatic order optimizer to selected starters;
- report internal competitive cost versus the unconstrained optimizer result.

The 0.5.7.2 execution engine uses a best-effort strategy:

1. Calculate the strongest unconstrained fixed-formation baseline with the existing
   optimizer.
2. Enforce hard availability, Rest, formation and goalkeeper constraints.
3. Fill full-training slots with the highest-value remaining 100% targets where
   possible.
4. Fill 50% training slots and non-training slots with the strongest legal remaining
   players, giving training priorities extra weight without making them fatal.
5. Optimize individual orders through the existing workspace/order behavior.
6. Recalculate planned coverage by adding the proposed lineup as assumed 90-minute
   second-match exposure.
7. Compare the proposed lineup against the unconstrained baseline to produce internal
   score, changed-starter and sector deltas.
8. Generate explanations for selected, partially covered, omitted, unavailable or
   already-completed priorities.

Ordinary priority conflicts are not terminal. For example, if six players are marked
100% but the chosen formation has only three full Playmaking slots, the planner still
returns the strongest legal lineup it can find, marks the full-slot capacity conflict,
and explains which targets were covered, partially covered or omitted.

The planner returns no lineup only when a legal lineup cannot exist, such as no
available players, no supported formation or no valid available goalkeeper.

## UI Workflow

The Squad page adds a Weekly Planner tab with:

- active training display;
- fixed formation selector;
- Generate Plan;
- Record Played Lineup when no first-match record exists;
- visible first-match record card with Edit, Replace and Delete when a record exists;
- Use This Lineup;
- one unified weekly player table;
- second-match Formation Board;
- competitive cost summary;
- explanations and warnings.

The unified table replaces the older separate Training Priorities and Weekly Coverage
tables. Its columns are Player, Age, Best Training Position, Priority, Training Status,
Confirmed, Planned, Remaining and Availability. Training Status uses plain symbols:
check mark for already trained, open circle for will train in the generated plan and
dash for will not train in the generated plan. Confirmed and Planned percentages remain
visible so the symbol is not the only source of information.

Alpha 0.5.7.3 hardens the result layout around a strict ownership contract:

- the shared Formation Board owns only the lineup workspace: pitch drawing, player
  cards, bench side panel, player-details side panel and lineup-editing overlays;
- Competitive Cost is an external card below the lineup workspace;
- Warnings are an external warning card below Competitive Cost;
- Explanations are an external card with a bounded read-only text area and internal
  vertical scrolling;
- no planner cost, warning or explanation text is placed inside the pitch widget, pitch
  overlay, player-card layer or Formation Board internals.

The result area is therefore:

1. result header;
2. lineup workspace with pitch, bench and player details;
3. Competitive Cost card;
4. Warnings card;
5. Explanations card.

Long explanation text wraps inside its card. The visible explanation area is capped so
verbose plans do not make the whole page thousands of pixels tall or cover player cards.
At supported desktop sizes, the lineup workspace keeps the primary vertical allocation,
while cost, warnings and explanations stay compact below it.

The planner never overwrites Squad Builder or Match Workspace output by itself. The user
must explicitly choose `Use This Lineup` to copy the proposed lineup into the Squad
Ideal XI board.

Changing priority, formation or first-match data invalidates the current proposal. The
next `Generate Plan` action builds a fresh recommendation from the current planner
state.

## Persistence

Planner data is stored as JSON under the HT Coach application data directory:

`weekly_training_planner.json`

The schema is versioned and currently stores:

- `schema_version`;
- `active_training_type`;
- `active_week`;
- `priorities`;
- `match_records`;
- `archived_weeks`.

Malformed or unreadable files return a safe default state with diagnostics.

## Localization

All visible planner strings pass through the existing localization catalog. English and
Spanish strings are provided for tab labels, priorities, coverage statuses, conflicts,
actions and summaries.

The weekly player table uses concise user-facing training-position labels such as
`GK 15.15`, `IM 25.59` and `W 24.28`. Internal Python tuples and raw enum names are not
shown to the user.

## Known Limitations

- Only Playmaking has automatic training rules in Alpha 0.5.7.
- Exact substitutions and partial minutes are not imported from Hattrick yet.
- First-match recording currently stores the visible planned board with assumed
  90-minute starter exposure.
- The competitive cost is an internal planning delta, not a Hattrick rating projection.
- The planner is fixed-formation first; best-allowed-formation planning remains a later
  extension.
- Best-effort priority selection is intentionally heuristic. It reuses the existing
  ranking and order behavior rather than introducing a new exhaustive training optimizer.
