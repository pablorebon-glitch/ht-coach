# Weekly Training Lineup Planner

Alpha 0.5.7 adds a weekly training planner to the Squad page. Alpha 0.5.7.2 adds
the Planner Execution Engine, so the planner now generates an actual second-match
lineup instead of behaving only as a validator. The first supported training type was
Playmaking.

Alpha 0.5.8.5 (Complete Training System) generalizes the underlying rule engine to
all 12 senior Hattrick training types via a declarative catalog — see "Training
Catalog" below. Playmaking's own behavior is unchanged: `rule_provider_for("PLAYMAKING")`
still returns the original, untouched rule class, not the catalog-driven one (see
docs/ROADMAP.md's Alpha 0.5.8.5 entry for why). Full localization for the other 11
types' explanation strings and the Match optimizer's training-aware trade-off modes
are not yet wired up.

UX-02 exposed the training-type selector itself in the UI: the Weekly Training
Planner's combo (both the visible tab and the hidden legacy tab kept alive for
compatibility) now populates from the canonical `TrainingType` catalog directly —
all 12 types, localized labels — and changing it persists immediately and
recalculates coverage on the next render. See docs/ROADMAP.md's UX-02 entry for the
week_id-orphaning bug this surfaced and how it was fixed
(`WeeklyTrainingAppService.set_active_training_type`).

The planner helps answer a practical Hattrick question: after the first match of the
training week, which second-match lineup covers the training priorities while keeping
the team competitive?

## Training Catalog

`engine/weekly_training/training_types.py` / `training_effects.py` /
`training_definition.py` / `training_catalog.py` declare all 12 senior training types
(General, Set Pieces, Defending, Scoring, Winger, Shooting, Short Passes, Playmaking,
Goalkeeping, Through Passes, Defensive Positions, Wing Attacks) as data — a
`TrainingDefinition` per type, mapping each canonical position (Goalkeeper, Central
Defender, Wing Back, Inner Midfielder, Winger, Forward) to a `TrainingEffect` (Full /
Reduced / Very Small / None) per trained skill. Multi-skill training (Shooting trains
both Scoring and Set Pieces, at different effect levels) and team-wide "every
participant" effects (General's form training; Set Pieces' base training) are both
modeled directly rather than special-cased. Individual orders never change which
canonical position a player trains as — a Forward with a Towards Wing order still
trains as a Forward.

`CatalogTrainingRules` implements the same `TrainingRuleProvider` interface the
original Playmaking-only class always has (`factor_for_position`,
`exposure_for_entry`, `capacity_for_formation`), so the Match Cup optimizer and
weekly coverage math work with any of the 12 types without themselves branching on
training type. `rule_provider_for(training_type)` resolves all 12 stable string
values; an unrecognized/future value returns `None` rather than raising, so an
unsupported training type degrades to a safe "unavailable" state.

## Scope

The optimization engine remains stable. The planner does not change rating formulas,
probability calculations, tactic behavior, order behavior or existing optimizers.

It uses existing roster import, player ranking, formation catalog, Formation Board and
automatic order support. New logic is limited to training-week state, training
exposure rules (now generalized across all 12 types), priority persistence, coverage
aggregation and constrained lineup selection.

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

Alpha 0.5.7.3.1 fixes the weekly-player filter so it uses stable UI data roles instead
of translated display text or stale persistence labels. Alpha 0.5.7.3.2 simplifies the
visible filter set to All, 100%, 50%, No priority, Already trained, Will train and Not
training. Filters are based on player id, visible priority key and training status.
Changing a priority immediately updates filter eligibility, and the selected filter
survives sorting and plan regeneration.

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

HF-07 tightens the bridge from Match Workspace to Weekly Planner: when the
manager saves a historical Match Record as Partido 1 or Partido 2, the
destination is the Sunday-Saturday training cycle containing the record's
own match date. The current application date is never used as an implicit
fallback for a historical save. If the match date is missing, the app asks
the user to enter it first instead of guessing a week.

This remains independent from the HT competitive season calendar, which is
Monday-Sunday and exists only for season/week context.

Confirmed played records, assumed played records and planned records remain distinct in
coverage output. Rollover archives the week marker while retaining match records for
history and diagnostics.

HF-10 makes the final saved lineup the only authority for weekly participation. When
a Match Workspace record linked to Partido 1 or Partido 2 is saved again, the Weekly
Planner does not patch player booleans or append another historical exposure list.
It rebuilds the linked weekly match record from the final saved Formation Board,
removes the previous record for that weekly slot/link and persists the replacement.
Coverage is therefore always derived as:

```text
current Partido 1 lineup
+ current Partido 2 lineup
= weekly participation
```

Prior optimizer recommendations, temporary drafts, deleted/replaced records and older
lineup versions do not contribute. Deleting one weekly match removes only that match's
participation and preserves the other match. Replacing a linked match may also move
the record to the training cycle matching the visible match date, using the same
date shown in the Match form.

For diagnostics, `WeeklyTrainingAppService.participation_provenance(player_id)` reports
which current weekly record and formatted slot explain a player's participation. This
is intended for tests/debugging; normal UI should keep using localized, user-facing
position and side labels rather than raw slot ids.

HF-10.1 repairs the remaining stale-source path: every service read now normalizes
weekly match records to a canonical view with at most one Partido 1 and one Partido 2
per training cycle. If a JSON file contains duplicate active records for the same
cycle/slot (for example an old Match 1 projection plus its replacement), load-time
repair keeps the last persisted slot record and removes the superseded active
projection. Coverage, required-player lookup, plan generation and diagnostics all read
from this canonical view, so no old lineup version is merged into the displayed weekly
table.

`WeeklyTrainingAppService.explain_weekly_player_state(player_id, players,
displayed_symbol)` returns an auditable dictionary with priority, confirmed/assumed/
planned exposure, source matches and Partido 1/2 slot provenance. A player with only
a 100% priority and no current lineup presence has no participation source. In the UI,
`✓` means already counted as played/assumed played, `○` means planned training from a
lineup not yet counted as played, and `—` means no current participation.

Alpha 0.5.7.3 validates first-match dates before a record can affect training
coverage:

- Past + Played counts as already played exposure. If exact minutes are unknown, the
  exposure is marked as assumed.
- Past + Planned remains planned exposure only.
- Today + Played requires explicit user confirmation before it counts as played.
  Without confirmation, it is stored as planned exposure.
- Future + Played is converted to Planned with a clear warning. Future matches never
  count as already trained.
- Editing, replacing or deleting the first-match record recalculates coverage from the
  current date/status combination.

Alpha 0.5.7.3.2 changes Edit into a lineup-editing workflow. The saved first-match
lineup is restored into the interactive Formation Board, including formation, starters,
slot ids, individual orders and order sides. `Record Played Lineup` becomes `Save
Lineup Changes` while editing. Saving replaces the existing first-match record in
place, preserves its metadata and reruns the same temporal validation before exposure
is recalculated. Cancel Editing exits without changing persistence. Any saved lineup
edit invalidates the generated second-match proposal, so the next recommendation must
be generated from the updated first-match record.

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
- calculate internal competitive cost versus the unconstrained optimizer result for
  diagnostics.

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
- compact training summary;
- explanations and warnings.

The unified table replaces the older separate Training Priorities and Weekly Coverage
tables. Alpha 0.5.7.3.2 keeps the table intentionally compact with exactly three
visible columns: Player, Priority and Training Status. Training Status uses plain
symbols: check mark for already trained, open circle for will train in the generated
plan and dash for not training in the generated plan. Detailed exposure remains in the
training summary and saved planner state rather than expanding the main table.

Alpha 0.5.7.3 hardens the result layout around a strict ownership contract:

- the shared Formation Board owns only the lineup workspace: pitch drawing, player
  cards, bench side panel, player-details side panel and lineup-editing overlays;
- Training Summary is an external compact card below the lineup workspace;
- Warnings are an external warning card below Training Summary;
- Explanations are an external card with a bounded read-only text area and internal
  vertical scrolling;
- no planner cost, warning or explanation text is placed inside the pitch widget, pitch
  overlay, player-card layer or Formation Board internals.

The result area is therefore:

1. result header;
2. lineup workspace with pitch, bench and player details;
3. Training Summary card;
4. Warnings card;
5. Explanations card.

Alpha 0.5.7.3.1 further hardens this flow by placing the Weekly Planner split content
inside a normal vertical scroll area. The result area is no longer forced into one fixed
tab-height viewport: the pitch keeps its natural Formation Board height, and the page
scrolls down to Training Summary, Warnings and Explanations. The lineup workspace must
finish before any result card is laid out.

Long explanation text wraps inside its card. The visible explanation area is capped so
verbose plans do not make the whole page thousands of pixels tall or cover player cards.
At supported desktop sizes, the lineup workspace keeps the primary vertical allocation,
while cost, warnings and explanations stay compact below it.

The primary visible summary is training-focused: required 100% targets covered,
required 50% targets covered, already-trained players, planned-to-train players,
missing priority targets and unavailable priority targets. Sector deltas and competitive
cost remain implementation diagnostics rather than prominent content over or beside the
pitch.

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

Planner warnings that originate as engine diagnostics are translated by the PySide6
presentation layer before reaching the label. This keeps engine behavior stable while
avoiding mixed English/Spanish UI text.

The weekly player table uses concise user-facing training-position labels such as
`GK 15.15`, `IM 25.59` and `W 24.28`. Internal Python tuples and raw enum names are not
shown to the user.

## Known Limitations

- Only Playmaking has automatic training rules in Alpha 0.5.7.
- Exact substitutions and partial minutes are not imported from Hattrick yet.
- First-match recording currently stores the visible planned board with assumed
  90-minute starter exposure.
- Competitive cost is an internal planning delta, not a Hattrick rating projection, and
  is not the primary visible Weekly Planner result.
- The planner is fixed-formation first; best-allowed-formation planning remains a later
  extension.
- Best-effort priority selection is intentionally heuristic. It reuses the existing
  ranking and order behavior rather than introducing a new exhaustive training optimizer.
