# Unified Match Workflow

Alpha 0.6.7 reorganizes the complete match workflow around one canonical
persistent Match Record (extending Alpha 0.6.6's `OfficialMatchRecord`
foundation, never a parallel entity). This document covers the pieces built
so far.

## The chronological navigation bug (Part 15) -- found and fixed

This sprint's brief explicitly called out "the inverted navigation/order
bug," and it was real: `engine/history/record_navigation.py`'s
`navigate_records()` (built in Alpha 0.6.6) sorted the record list
newest-first, but its "previous"/"next" arithmetic treated `index - 1` as
"previous" and `index + 1` as "next" -- raw array-index directions, not the
chronological meaning the buttons are labeled with. Since index 0 is the
*newest* record in a newest-first list, clicking "Partido anterior"
(previous, which should mean *older*) from the newest record did nothing
(it was already at index 0), and clicking "Partido siguiente" (next, which
should mean *newer*) moved it to an *older* record -- exactly backwards.

Fixed by inverting the index arithmetic to match the semantic meaning: in a
newest-first list, moving to an *older* record means *incrementing* the
index, and moving to a *newer* one means *decrementing* it.
`can_go_previous`/`can_go_next` were fixed to match. Every existing test that
encoded the old (buggy) array-position semantics was rewritten to assert on
**actual dates** instead, per the brief's own explicit instruction ("tests
must verify actual dates, not array positions") -- this is exactly the kind
of bug a position-based assertion can't catch, since the wrong code and the
wrong test agreed with each other.

## Deterministic ordering for unknown dates (Part 15, continued)

`list_records()`'s sort key changed from a single fallback
(`match_date or created_at`) -- which could interleave a date-less record
anywhere among dated ones depending on when it happened to be created -- to
an explicit three-part key: `(has_known_date, match_date, snapshot_id)`.
Records with a known date always sort before records without one, and
`snapshot_id` is an explicit, stable tiebreaker so the order never changes
between runs.

## Status invariant, made explicit (Part 16)

`derive_match_record_status()` (Alpha 0.6.6, Part 12) already only ever
returned `COMPLETE` through one code path requiring both official PRE and
POST -- the invariant "COMPLETE requires official_post != None" held
structurally already. Alpha 0.6.7 makes it an explicit, always-checked
assertion (`assert_status_invariants()`) rather than an implicit property of
the code's control flow, so a future change that violates it fails loudly
instead of silently shipping a wrong status. Verified exhaustively across
every realistic combination of official PRE / POST / retrospective PRE /
match date.

## Provisional identity collision safety (Part 2)

The brief warns against exactly the bug of concatenating raw IDs without a
delimiter (`opponent 1 + competition 1 = "11"`, colliding with a different
combination). `compute_provisional_identity()` (Alpha 0.6.6, Part 11) was
already built with an explicit delimiter and named fields
(`season:week:date:opponent:competition`), which structurally prevents this
class of collision -- verified with a test using the brief's own numeric
example. `models/opponent.py`'s `Opponent` has no separate stable ID field
today (opponents are keyed by name throughout the existing architecture, in
`OpponentRepository` and everywhere else) -- introducing one is a larger,
separate architectural change than this identity function alone, and isn't
needed for the specific collision risk the brief describes, which is already
closed.

## Expandable "Partido" submenu (Part 3)

`NavigationSidebar` gained expandable group support -- a page dict may now
include a `"children"` list, whose items render indented right after the
parent when expanded (a plain click toggles). Every existing flat page keeps
navigating exactly as before; groups themselves never emit
`navigation_requested`, only their leaf children do.
`MainWindow.PAGES` now nests the existing Match page and the new Saved
Matches page under a single "Partido" group. `select_page(key)` auto-expands
the right parent group when navigating directly to a child (e.g. from
another part of the app), and both `retranslate_ui()` and group-toggling
preserve whatever was currently selected -- rebuilding the list never
silently loses the active page.

## Saved Matches management list (Part 7)

`SavedMatchesPage` + `SavedMatchesController`: a genuine management list --
opening it never auto-opens the latest match, matching the brief's own
explicit requirement. Reads from the exact same canonical
`HistoricalMatchRepository` Official Match History already uses (via the
Alpha 0.6.6 `list_records()`), never a second store. Each row identifies the
match only (`"CA Chaco — Liga"`, matching the brief's own example
character-for-character) -- status lives in its own column, never appended
to the identity text (verified explicitly: no status word ever appears in
the opponent cell). Edit/Delete stay disabled until a row is selected.

HF-09 makes the edit flow explicitly isolated from New Match preparation.
Selecting "Partido nuevo" creates a fresh draft workspace and clears any
previous result area. Editing a row from Saved Matches opens the same Match
workspace shell, but the active analysis owner is the saved record's
`snapshot_id`; cached results are restored only when they were saved for that
exact record. A previous New Match analysis can no longer remain visible under
saved-match metadata.

HF-10 extends this to Weekly Planner participation. If a saved match is linked to
Partido 1 or Partido 2 and the manager saves a changed final lineup, the linked
weekly record is replaced from that final lineup. The previous participation
projection is removed before the new one is applied, so removed players no longer
count as played/trained. Reanalysis alone does not update Weekly Planner; the
change takes effect only when the saved match is explicitly saved.

Match preparation now follows the fixed match-specific order: Rival, Tipo de
partido, Localia, Fecha del partido, Formaciones, formation action buttons,
Analizar partido. CSV and availability remain above that block as global
preparation inputs. New Match dates come from the injected application calendar;
Saved Match edit restores the exact saved date.

## Create-or-open-existing detection, and duplicate conflicts (Parts 5-6)

`engine/history/match_lookup.py`'s `find_existing_or_conflicting_record()`
runs before a new analysis starts: an *exact* match on the typed
provisional identity means "you're re-analyzing something you already
have" (Part 5's dialog, word-for-word: "Ya existe un análisis para este
partido. ¿Querés editar el análisis existente?"); same opponent + same date
or HT week but a *different* competition type means "you probably saved
this same match twice by mistake" (Part 6's dialog, reproducing the brief's
own CA Chaco/Copa/Liga example). Wired into `MatchController._analyze()` --
confirming "Sí" navigates to Saved Matches and opens the exact record (via a
new `AppEvents.open_saved_match_requested` signal); "No" resets the
opponent selector and creates nothing; the conflict dialog's three explicit
choices (Cancelar/Corregir/Crear otro partido) either change nothing,
update the existing record's competition type in place (never duplicating
it), or let a genuinely new analysis proceed.

**Known scope limitation**: the current Match workspace has no date or
season/week selector of its own yet (that's Part 4's New Match screen,
still to come), so today's detection uses today's date and omits season/week
from the lookup -- it correctly catches same-day duplicates but can't yet
distinguish two matches against the same opponent on different HT weeks by
season/week alone. This will tighten once Part 4's dedicated fields exist.

## Duplicate record reconciliation (Part 17)

`engine/history/duplicate_reconciliation.py` fixes exactly the scenario the
brief names -- "two CA Chaco records". Detection uses evidence strength in
order: (1) same official Match ID (strongest -- checked first, and records
grouped this way are never reconsidered by the weaker signal below), then
(2) same opponent + same date/HT week with no Match ID yet (e.g. two
provisional records for what's genuinely the same planned match). A group
is only auto-mergeable when **at most one** record in it carries each piece
of official evidence (PRE/POST/Match ID) -- two records that each carry
their *own*, different POST is treated as a genuine conflict and never
silently resolved; it comes back in the report instead. Safe merges keep
the *oldest* record's identity (the most established one) and pull in the
richest non-conflicting field from every duplicate -- verified with the
brief's own named fixture (two CA Chaco records sharing a Match ID, one
carrying the POST, the other carrying season/week metadata) to merge into
one record with zero data loss. `reconcile_duplicates()` never partially or
silently fixes anything -- it always returns an explicit
`ReconciliationReport` naming exactly what was merged and what remains
unresolved for manual attention.

## Delete Saved Match (Part 9)

`engine/history/match_deletion.py` deletes the canonical record and
everything it owns in one step -- PRE, retrospective PRE, POST, comparisons,
conclusions and revision history are all embedded fields on the same
`HistoricalMatchSnapshot`, so removing it can never leave an orphan PRE/POST
snapshot behind. Wired into `SavedMatchesPage`/`SavedMatchesController` with
Part 9's own two-tier dialog: the first confirmation reproduces the brief's
exact wording ("¿Eliminar definitivamente este análisis?" plus the full
explanation of what may be removed); if a linked Weekly Planner record is
found, a second dialog offers the explicit three-way choice ("Cancelar" /
"Borrar solo análisis" / "Borrar análisis y registro semanal") -- "analysis
only" preserves the weekly record untouched, "both" removes it too, and
cancelling at either step deletes nothing.

**Known scope limitation, matching Part 5-6's own note**: Weekly Planner
doesn't yet store a canonical Match Record ID reference (that's the fuller
Part 19), so the link is inferred by opponent name + match date -- the best
signal available today. `find_linked_weekly_match_records()` is isolated
specifically so it can be swapped for a direct ID lookup once Part 19 lands,
without touching the deletion or dialog logic around it.

## Selector shows identity only, never status (Part 14)

Found a real violation in my own Alpha 0.6.6 work: the Official Intelligence
record selector's dropdown label included the status word
(`"{date} — {opponent} — {status}"`), which this sprint's Part 14 explicitly
forbids. Fixed to match the brief's own worked example exactly --
`"CA Chaco - Hit'em up"` (opponent + our own team name, read from whichever
of official PRE/POST/retrospective PRE actually has it). A provisional
record with no evidence yet has no team name to show, so it falls back to
the match date -- never a status word filling that gap. The full metadata
(HT season, competitive week, date, competition type, status, Match ID) was
already living separately in the identity block below the selector since
Alpha 0.6.6 -- that part needed no change, only the selector label itself.

## Edit, connected (Part 8)

`MatchController.edit_record(snapshot_id)` opens the same Match analysis
workspace used for a new analysis -- pre-populated with the saved
opponent and competition type (formation/lineup restoration needs a fuller
mapper from `HistoricalLineupEntry` to the workspace's own board
representation, not yet built, and isn't populated on records created
through the Part 11 provisional flow today). Tracks which record is being
edited via `_editing_snapshot_id`; Part 5's own "an analysis for this
already exists" check now skips itself when the exact match it finds *is*
the record currently being edited, so re-analyzing what you're editing
never asks you to confirm opening what you already have open -- while a
genuinely different match (switching the opponent mid-edit) still triggers
normal detection exactly as before.

## PRE import relocated beside the pitch, compact ratings panel (Parts 10-12)

`MatchPage` gained a persistent side panel next to the formation board --
built once, reused across re-analysis just like the board widget itself.
The "Importar resumen oficial" button was *moved* there (removed from the
old setup-form grid position, not duplicated), visually associated with the
lineup being prepared. Below it: a red warning ("Falta importar el PRE
oficial") before any Official PRE exists for this context, replaced by a
normal-styled confirmation ("PRE oficial cargado") once it does --
`MatchController._update_pre_status_and_ratings_panel()` checks this the
same way `_apply_official_pre_if_available()` already does, so both stay
consistent. Once PRE exists, a compact Hattrick-inspired ratings panel
appears in the same side panel -- Defense (left/central/right), Midfield,
Attack (left/central/right), Tactic, Tactic Level, and Formation/Team
Attitude when available -- verified end-to-end with realistic parsed PRE
data. Structural check confirms the pitch and side panel are two distinct
widgets in one horizontal layout, never overlapping.

## State-dependent import from Official Intelligence (Part 13)

`MatchIntelligenceController._import_dialog_defaults()` reflects the
currently selected record's own state, matching the brief's four cases
exactly: no evidence at all -> plain PRE default, no hint; PRE exists, POST
missing -> defaults to POST with a hint explaining why; POST exists, PRE
missing -> defaults to PRE, with the hint distinguishing a still-future
match (normal PRE import) from an already-played one (explaining that
pasting a reproduced formation now will be offered as a retrospective
simulation, via the existing Alpha 0.6.6 flow -- never a separate
mechanism); Complete -> a hint explaining that replacing either slot
requires confirmation, while the existing
`OfficialRatingReplaceConfirmationRequired` flow still runs unchanged
underneath (this only sets a sensible starting radio choice, it never
bypasses that confirmation or silently overwrites anything).
`MatchIntelligenceImportDialog` gained `default_slot`/`hint_text` parameters
to display this.

## Import actions from Official Intelligence, state-aware (Part 13)

Already built in an earlier pass of this sprint: `_import_dialog_defaults()`
picks the pre-selected slot (and an explanatory hint) from the currently
selected record's own state -- Complete records default to "pre" with a
warning that either replacement needs confirmation; PRE-only records
prioritize "post"; POST-only records offer "pre", with a hint distinguishing
a still-future match (normal PRE) from an already-played one (hinting that a
reproduced-formation paste will be offered as retrospective, matching the
existing Alpha 0.6.6 flow) -- never guessing incorrectly, always deferring
to the existing replace-confirmation dialog for the actual overwrite.
Verified with 8 existing tests.

## Full canonical link, Weekly Planner to Match Record (Part 19)

`WeeklyMatchRecord` gained an additive `linked_match_record_id` field
(roundtrips through persistence; a weekly record saved before this field
existed just loads with it empty, verified against a hand-written legacy
payload). `find_linked_weekly_match_records()` (Part 9's deletion) now
checks this strong ID link first, only falling back to the opponent+date
inference for weekly records that predate it -- and a record already linked
to a *different* canonical ID is never re-claimed by the weaker inference,
even if names/dates happen to coincide.

`MatchController._linked_canonical_record_id()` populates it at save time:
if a specific record is already being edited, that's the link, no lookup
needed; otherwise it finds or creates the provisional record for this exact
match (reusing Part 11's own creation flow) -- verified end-to-end that
saving from Match creates exactly one canonical record and links the weekly
entry to it, and that saving again (even after a "replace" confirmation)
never creates a second one.

## Canonical Weekly Planner link (Part 19)

Found already substantially built and tested from earlier work this
sprint: `WeeklyMatchRecord.linked_match_record_id` (additive, defaults to
empty, backward compatible with legacy persisted records) stores the
canonical `HistoricalMatchSnapshot` a weekly entry belongs to.
`MatchController._linked_canonical_record_id()` resolves it when saving --
the record currently being edited if one is, otherwise finding or creating
the provisional record for the exact match via Part 11's own flow, so
saving from Match never creates a second, disconnected weekly-only
identity. `find_linked_weekly_match_records()` (Part 9's deletion flow) now
prefers this canonical ID over the opponent+date inference, falling back to
inference only for records saved before this field existed -- and never
lets the weaker inference re-claim a record already linked to a *different*
canonical record. Only a stale module docstring needed fixing (it had
described the fuller link as "not yet built").

## Migration, orchestrated (Part 20)

`engine/history/migration.py`'s `migrate_to_unified_workflow()` combines
everything this sprint already built into one explicit pass with a report:
backward-compatible loading (nothing to do -- already structural),
duplicate reconciliation (Part 17, reused as-is), and a defensive per-record
check that the COMPLETE-requires-POST invariant (Part 16) actually holds --
which it always does structurally, but this pass verifies it directly
rather than assuming, and reports anything unexpected instead of crashing.
Verified with a realistic mixed scenario: pre-sprint legacy records loaded
alongside a genuine Chaco-style duplicate pair, migrated together in one
pass, reconciled correctly, and reported as clean.

## New Match's own date selector (Part 4, closing)

`MatchPage` gained a real `QDateEdit` field (defaulting to today, calendar
popup, `yyyy-MM-dd` display) -- the underlying detection/creation logic
(Parts 5-6, 11) was already built around a `match_date` parameter; it was
only ever being fed a hardcoded `date.today()` because there was no field
to read a real one from. `_should_stop_for_existing_or_conflicting_match()`
and `_linked_canonical_record_id()` both now read the view's own
`match_date()` when available. This closes a real gap the fixed date
couldn't: two matches against the same opponent on genuinely different
dates no longer risk being conflated, and `edit_record()` restores the
saved date alongside opponent and competition type.

## Edit's workspace restoration, closing note (Part 8)

Investigated fully rebuilding the formation board from `HistoricalLineupEntry`
and concluded it's the wrong target: `HistoricalMatchSnapshot` is a thin,
denormalized history record, never meant to carry a fully re-analyzable
workspace (boards, ratings, optimizer output, `WorkspaceState`'s history/
redo stacks). That full state exists only in `MatchWorkspaceRepository`'s
single "last analyzed result" slot, which isn't keyed per canonical record
today. Implemented the honest, best-effort version instead: if that cached
result happens to match the record being edited (the common case right
after saving), `edit_record()` restores it in full via the same
`show_results(..., restored=True)` path already used elsewhere; otherwise
it tells the user plainly that a fresh analysis is needed, rather than
silently showing nothing or -- worse -- stale data from an unrelated match.
Per-record workspace persistence (so this always works regardless of what
was analyzed most recently) would be a genuinely separate, larger
architectural change beyond this sprint's scope.

## Sprint status: all 27 parts addressed

## HF-02: Match Record Integrity, Season Calendar and Match UX Completion

A repair sprint over Alpha 0.6.7's own real-use regressions, found through
manual verification rather than new feature work.

### Delete no longer leaves orphaned evidence (HF-02 Part 1)

Root cause: `MatchWorkspaceRepository`'s single "last analyzed result" cache
can carry Official PRE data already merged into its sector comparisons
(`apply_official_pre_override`). Deleting the canonical record never cleared
this separate cache, so re-opening Match after a delete could show the old
PRE resurrected. `MatchWorkspaceRepository.clear_last_result()` + wiring
through `delete_saved_match()`/`SavedMatchesController` now clears it --
only when the cached result is for the same opponent being deleted, never an
unrelated match. Verified with the brief's own exact 6-step scenario
(create -> PRE -> POST -> delete -> recreate -> no resurrection).

### Individual orders are now editable in the real Match UI (HF-02 Part 2, blocking)

Root cause: `PlayerCard` only ever handled selection and drag-to-swap --
there was no order-editing control anywhere in the interactive board, even
though `WorkspaceService.set_manual_order()`/`valid_orders_for_position()`
(Alpha 0.6.6) were fully built and unused. Added a `QComboBox` to the
inspector panel for the selected on-pitch player, populated from
`valid_order_configurations_for_position()`, wired to the exact same
`workspace_modified` signal the existing replacement flow already uses --
which was already connected to the full recalculation pipeline, so tactical
calculations, the pitch, and the saved record all refresh with no new
plumbing needed. Verified against the brief's own manual scenarios (central
defender, forward, goalkeeper) and confirmed unrelated players' orders never
change.

### Match date now threads through to Weekly Planner saves (HF-02 Part 3, resolved)

Root cause confirmed: `record_first_match`/`record_second_match` always
derived their `match_id` from `state.active_week.week_id`, never from the
match's own scheduled date -- and the controller never even passed the
selected date through.

**First attempt (later superseded)**: made `match_id` derive from the
target date via a hand-rolled anchor computation off `state.active_week`,
avoiding a second, uncontrolled call to `active_training_week()`. This
broke 6-9 pre-existing tests in `tests/test_weekly_training_planner.py` --
not because the anchor math was wrong, but because those tests hardcoded
fixture dates (`date(2026, 7, 21)`) that were written assuming "today"
would land near them; wall-clock time had since moved past those dates
entirely, and `WeeklyTrainingAppService.load_state()` re-derives
`active_week` against *real* time on every call regardless of what a test
seeds. Fixed the tests properly instead of hiding the problem: added
`_dates_within_current_week()`, which computes fixture dates relative to
whatever the actual active week is at the moment the suite runs, so they
never drift into the past again.

**A second, genuine edge case** surfaced once those tests passed: the
Thursday training-update cutoff means `active_week.end_date` marks that
cutoff, not the calendar week's actual end -- so on a Friday/Saturday,
"today" itself can fall *before* `active_week.start_date` (rollover has
already advanced to the following Sunday). A hand-rolled range check
against `active_week`'s own boundaries got this wrong for the ordinary
"save today's match" case. Fixed by reusing the *exact same*
rollover-aware algorithm `active_week` itself was computed with
(`active_training_week(today=target_date, ...)`) rather than a bespoke
boundary comparison -- since both sides evaluate the identical rule against
the same effective date, they can never disagree for "today's match," while
still correctly resolving a genuinely different (historical or future)
week's identity when the date actually is one. Added an explicit
regression test for this.

The confirmation dialog (`_target_week_range()`) and the record's own
`match_id` now derive from the exact same logic
(`WeeklyTrainingAppService.week_start_date_for()`), so they can never
disagree about which week is actually being affected.
`tests/test_match_date_weekly_targeting.py` and
`tests/test_weekly_training_planner.py` cover both the historical-date
case and the rollover edge case.

### Canonical metadata correction while editing (HF-02 Part 4)

Found a real gap: `edit_record()` already restored opponent/date/type to
the setup form, but saving corrections back only ever persisted the
*lineup* onto the canonical record (`_persist_lineup_to_canonical_record`,
HF-01 Part 8) -- date/competition-type/venue-role corrections made while
editing were silently discarded. Added `_persist_metadata_corrections_to_
canonical_record()`, run whenever `_editing_snapshot_id` is set (i.e.
genuinely editing an existing record, never a brand-new match), which
writes the current form's date/competition type/venue role back onto the
same record's `MatchContext` -- verified to never touch the official Match
ID or opponent identity, and never create a duplicate record. Also restored
venue role to the form on Edit (Part 5's own field, not yet wired into
`edit_record()` until now).

Found and fixed a real test-isolation bug of my own while building this:
one of my new tests omitted an explicit, isolated `WeeklyTrainingRepository`
for `WeeklyTrainingAppService`, so it fell back to the shared, real
user-data-directory path -- letting state leak across test runs and, once
"CA Chaco" already had a saved first match from an earlier run, causing a
genuine but *unmocked* `duplicate_match_id` confirmation dialog to block
headless test execution. Fixed by isolating the repository the same way
every other test file in this sprint already does.

### VenueRole and the central match display formatter (HF-02 Parts 5-6)

Found that `HomeAway` (`HOME`/`AWAY`/`NEUTRAL`/`UNKNOWN`) already existed on
`MatchContext` -- the exact same concept the brief calls "VenueRole" -- but
was never surfaced anywhere: no UI selector, never set, never displayed.
Reused it rather than inventing a parallel enum. Added a `QComboBox` to New
Match (defaulting to Unknown -- never guessed), wired through
`find_or_create_provisional_record(home_away=...)` so it persists on the
canonical record.

`ht_coach_app/services/match_display_formatter.py` is the one central
formatter the brief asks for: `format_match_identity()` for the "vs."-style
full identity (respecting venue role -- home shows our team first, away
shows the opponent first, neutral appends "· Neutral", verified against all
four of the brief's own worked examples exactly), and
`format_match_selector_option()` for the "-"-style compact selector label
("pata2008 - Hit'em up", matching the brief's own example). Official
Intelligence's own selector formatting (`_format_record_option`, HF-01 Part
14) was refactored to call this central function rather than building its
own string -- reducing exactly the kind of divergent, duplicated-fragment
risk the brief's reported bug describes, even without a confirmed repro of
the original bug's exact trigger.

### Saved Matches shows Venue (HF-02 Part 7)

Found the table was missing a Venue column entirely (the brief's own
required list: Rival/Type/Date/Season-Week/Venue/Status). Added it as the
6th column, using the same `HomeAway`/`VenueRole` value Part 5 introduced
-- the existing date/type/season-week columns already correctly showed
real values (never "Unknown" when derivable), so this was purely the
missing column, not a broader display bug.

### Duplicate detection now respects venue (HF-02 Part 9)

The weaker (no Match ID yet) duplicate-grouping signal previously matched
on opponent + date + HT week alone -- missing the brief's own explicit
identity criterion #3 ("same opponent + scheduled date + venue + overlapping
evidence"). Added venue to the grouping key: a home leg and an away leg of
the same two-leg cup tie, same opponent, same week, are now correctly never
grouped as a duplicate just because everything else matches. Records that
share the same venue (the common case) are still detected exactly as
before.

### Duplicate resolution surface, for real (HF-02 Part 10)

`reconcile_duplicates()` (Alpha 0.6.7, Part 17) already correctly refused
to silently merge ambiguous conflicts -- it just had nowhere to send them.
Added `resolve_duplicate_group_manually()` (the person picks which
record's conflicting evidence wins; non-conflicting metadata from the
other still gets folded in, same as auto-merge) and a "Buscar duplicados"
button on Saved Matches that runs reconciliation, reports how many were
merged automatically versus how many still need a choice, and shows each
ambiguous group one at a time with a plain description of every candidate
record -- an explicit "omitir" option leaves a group untouched rather than
forcing a decision. Verified end-to-end: choosing a record keeps its own
conflicting evidence while still inheriting the other's non-conflicting
metadata; skipping loses nothing; a safe-merge and an ambiguous conflict in
the same run are reported as distinct counts.

### HT Season Calendar (HF-02 Parts 11-13)

Built the full configuration + deterministic resolution + recalculation
stack -- see `docs/HT_SEASON_CALENDAR.md` for the complete writeup. In
short: `resolve_season_context(match_date, config)` derives Temporada HT /
Semana competitiva from an explicitly configured season anchor, never
guesses without one, and stays completely separate from the training-cycle
calendar. Verified against all of the brief's own acceptance scenarios.
Configuration UI lives at Configuracion -> Calendario de temporada HT.
Not yet wired into New Match's own season/week preview or into the deeper
Part 3 fix it was meant to eventually unblock -- see the doc's own closing
note.

### Compact "Calificaciones" card redesigned (HF-02 Part 15)

The panel already correctly avoided titling itself "PRE oficial" (that
wording stayed in the separate status line beside it, per Part 16's own
distinction -- a workflow status line, not the card itself), but two real
gaps remained: the title said "Ratings oficiales" rather than the brief's
own required "Calificaciones", and every value used a verbose
"Izquierda:"/"Central:"/"Derecha:" text label rather than the brief's own
explicit instruction that spatial position alone should communicate the
sector. Rebuilt `show_compact_official_ratings()` around a 3x3
`QGridLayout` -- defense row (left/central/right columns), midfield
(centered), attack row (left/central/right) -- with bare numeric values,
no sector labels at all. Verified none of the forbidden verbose labels
appear anywhere in the panel, and that each value lands in its correct
grid cell.

One genuine gap remained under the "honest, best-effort" restoration
described above: nothing was saving a lineup/tactic *summary* onto the
canonical record itself, so Edit had nothing of its own to fall back on
beyond the single cached workspace slot. Closed this pass:
`engine/history/lineup_snapshot.py` converts a `FormationAnalysisResult`'s
own recommended lineup into `HistoricalLineupEntry`/`TacticalSetup` --
never a full board-state duplication, just player/position/order and
formation/tactic/level.
`MatchController._persist_lineup_to_canonical_record()` saves this
whenever the canonical record ID gets resolved (both the "editing an
existing record" and "find-or-create" paths), so a canonical record now
carries a real summary of what was planned for it, independent of whatever
happens to be in the single-slot cache -- and never creates a duplicate
record doing so.

With this, all 27 parts of Alpha 0.6.7 have an engine-level implementation,
tests, and -- for every part with a user-facing surface -- real UI wiring.
Full suite: 2006 passed / 0 failed.

### Compact "Calificaciones" card, one more fix (HF-02 Part 15, continued)

Found one more real gap while running Part 21's own manual acceptance
scenario F: the brief's worked example explicitly shows the card itself
containing "No cargadas" before PRE exists (`Calificaciones / No cargadas /
[Importar resumen oficial]`), but the panel was simply staying empty
instead. Fixed `show_compact_official_ratings(None)` to render the title
plus a "No cargadas" line within the card, matching the brief's own
example exactly. Updated the two existing tests that had asserted the old
(incorrect) "stays empty" behavior.

### Manual acceptance checklist (HF-02 Part 21)

Ran each of the brief's own scenarios against real code, not just unit
tests in isolation:

- **A. Delete/recreate**: create -> PRE -> POST -> delete complete analysis
  -> recreate same opponent/date/type -> confirmed no PRE, POST, or Match ID
  reappears. PASS.
- **B. Orders**: selected a central defender on a real `FormationBoard`,
  changed order to Offensive via the new selector, confirmed it applied to
  that slot. PASS.
- **C. Historical week**: RESOLVED (see Part 3 above, now fully fixed). Saved
  a match dated 2026-07-26 as Match 1, confirmed its `match_id` correctly
  resolved to the training cycle containing that date, not the currently
  active week.
- **D. Metadata**: created a record with date/venue/season-week, completed
  it with PRE+POST, confirmed Saved Matches' own row formatter shows the
  real date, venue ("Local"), and season/week -- never a fabricated
  "Unknown" for values that were actually known. PASS.
- **E. Season config**: configured season 95 starting 2026-07-27, confirmed
  2026-07-27 resolves to week 1 and 2026-08-03 resolves to week 2. PASS.
- **F. Ratings card**: confirmed "No cargadas" (now fixed, see above) before
  PRE, and the spatial grid of real values after. PASS.
- **G. History**: confirmed the central selector formatter never produces
  duplicated name fragments for the brief's own worked example. PASS
  (chronological previous/next semantics themselves were already fixed
  and tested in the original Alpha 0.6.7 sprint, Part 15).

## Alpha 0.6.7 HF-03: Match Workspace Isolation, Formation Save and Tactical Controls

### Root cause of PRE leakage between records (HF-03 Parts 1-3, 11)

Found the genuine, severe root cause: `_latest_official_pre_ratings()` and
`_update_pre_status_and_ratings_panel()` (both from HF-02) resolved via
`service.latest_snapshot_with_official_data()` -- "whichever record
anywhere in the whole database was most recently touched" -- with no
regard for which match the workspace actually had open. A brand-new,
completely unrelated match would silently inherit another match's Official
PRE the moment *any* analysis ran, since that other record simply happened
to be the most recently updated one globally.

Fixed by introducing `_current_workspace_record()` -- the one, single
source of truth for "which canonical Match Record does this workspace
currently represent." Both the PRE-application logic and the Calificaciones
card now resolve through it exclusively: the record being edited
(`_editing_snapshot_id`) when one is set, otherwise the record matching the
current opponent + date (the same identity `_should_stop_for_existing_or_
conflicting_match` already uses), with a fallback to the currently
displayed analysis result's own opponent name when the selector combo
hasn't been separately populated. Never a database-wide "most recent"
fallback.

Verified against Part 11's own exact acceptance scenario: create Match A
(no PRE), create Match B (with PRE), reopen Match A -- A shows no PRE from
B. Also verified the "still works correctly" case: reopening a record that
genuinely has its own PRE still shows it.

### Cross-controller event scoping (HF-03 Part 17)

`AppEvents.official_ratings_changed` used to carry no data at all --
any listener would blindly refresh regardless of which record was actually
touched. Extended to `Signal(str)` carrying the touched record's own
`snapshot_id` (from `ImportOutcome.snapshot`, threaded through from both
Match's own import and Official Intelligence's). The Match controller's
listener now explicitly verifies the touched record matches what it
currently has open (`_current_workspace_record()`) before refreshing --
an event for an unrelated match is silently ignored, exactly as the brief
requires ("receivers must ignore events for other records").

### Regression note

Fixing the root cause above required updating several pre-existing HF-02
tests whose setup relied on the old, unscoped lookup (e.g. not setting a
matching opponent/date on the page, since previously any PRE anywhere would
apply regardless). Fixed each to properly set up a matching workspace
context rather than loosening the new, correct scoping.

### "Guardar formación" -- independent from Weekly Planner (HF-03 Parts 5-6)

Added the button between "Restaurar alineación optimizada" and "Guardar
como Partido 1" (the brief's own suggested position). Persists straight
onto the canonical Match Record -- lineup, positions, individual orders,
formation, tactic, tactic level -- reusing the same `_current_workspace_
record()` resolution and `_persist_lineup_to_canonical_record()`/
`_persist_metadata_corrections_to_canonical_record()` machinery already
built for editing. Creates a fresh provisional record on the spot when
none exists yet (the common case for a genuinely new historical match).
Never touches `WeeklyTrainingAppService` -- verified explicitly that saving
a formation leaves the weekly planner's own match records untouched.
HF-10.5 changed the enablement rule from "dirty only" to "valid saveable
workspace": a save requires opponent metadata, match type, match date, a
non-stale analysis result and a recommended lineup. Disabled buttons expose
the blocking reason as a tooltip.

HF-10.5 also centralizes the write path. `Guardar formacion`, `Guardar como
Partido 1` and `Guardar como Partido 2` first call the same canonical save
transaction, which persists structured match metadata plus the lineup to one
`HistoricalMatchSnapshot` and returns the saved ID/revision. Weekly saves then
link Partido 1/2 to that ID. If the weekly write fails after the canonical
record was saved, the Match page remains in saved-edit mode with the same
board/results visible and reports the link error so the user can retry.

HF-10.6 closes the matching read path. Editing a Saved Match restores the
competition selector from canonical item data, venue from canonical
`HomeAway`, the saved CSV source into the roster loader, and the Formation Board
from the persisted lineup/tactical setup when no matching cached analysis result
exists. This shows "Formacion guardada restaurada" instead of requiring Analyze
only to view the saved XI.

Verified end-to-end against Part 11's exact scenario: create a historical
match, save its formation, reopen from a brand-new controller instance
(simulating navigating away and back), confirm opponent/date/formation/
tactic all restore correctly.

### Canonical tactic/team attitude selectors (HF-03 Parts 7-8)

Added tactic and team attitude selectors to the formation board's header,
next to the existing formation selector. Tactic reuses the pre-existing
`models.tactic.Tactic` enum (7 canonical values, matching the brief's own
list exactly -- never invented). Team attitude is a new
`models.team_attitude.TeamAttitude` enum (3 values, also matching the
brief). Both mark the workspace dirty on change (enabling "Guardar
formación"), never touch player selection or individual orders, and never
mutate Official PRE -- verified explicitly against a record with existing
PRE evidence. The user's own selection overrides the optimizer's
recommendation when saving.

Found and fixed a real pre-existing gap while wiring this: my new
`match.tactic.*` localization namespace collided with an existing
`match.tactic` key (a comparison-table column header) that, on
investigation, had never actually had a value -- that header had been
silently showing "translation unavailable" text before this fix. Renamed
the new namespace to `match.tactic_option.*` and gave the original key its
real value ("Táctica"/"Tactic").

Deliberately did not attempt full rating/probability recalculation when the
tactic changes -- the existing architecture has no safe entry point for
"re-run analysis for this specific user-chosen tactic" without touching the
protected optimizer internals (`MatchWorkspaceService.analyze()` always
evaluates every tactic per formation and returns its own recommendation, it
does not accept a tactic override). Built the safe, honest subset instead:
selector, persistence, dirty-tracking, and isolation from Official PRE.

### Tactic mismatch indicator, PRE as evidence (HF-03 Parts 9-10)

Added a warning label near Calificaciones, shown only when the current
plan's tactic genuinely differs from Official PRE's own tactic -- using the
brief's own exact wording. Verified against the brief's own worked example
(plan AIM, PRE AOW) character-for-character. Confirmed importing PRE never
silently overwrites the current plan's tactic, lineup, or orders -- Part
9's own core requirement. The indicator always resolves through the same
`_current_workspace_record()` isolation fix as everything else in HF-03,
so it can never compare against an unrelated record's PRE.

### Unsaved changes flow (HF-03 Part 12)

Switching to a different Saved Match while the current workspace has
unsaved changes (`FormationBoard.is_dirty()`, the same flag already
enabling "Guardar formación") now prompts with the brief's own exact
wording -- Cancelar / Descartar cambios / Guardar formación. Cancel stays
on the current record untouched; Discard switches with no persistence;
Save calls the same `_save_formation()` before switching. Re-opening the
*same* record that's already open is never treated as a "switch" and never
prompts. Verified explicitly that changes never transfer onto the new
record regardless of which choice is made.

### Crash diagnostics and recovery snapshots (HF-03 Parts 13-16)

Built the full diagnostics stack: `ht_coach_app/diagnostics/` (event
buffer, active context tracker, crash reporter, crash dialog, recovery
snapshot store). Installed the crash handler in `ht_coach_app/app.py`'s own
`run()` -- the real GUI entry point. Verified end-to-end with a simulated
exception that the crash log contains every field the brief requires. Full
details in docs/CRASH_RECOVERY.md and docs/MATCH_WORKSPACE_STATE.md.

### HF-07: retrospective evidence cannot rename the match

The canonical Match Record owns the historical opponent, date, competition,
venue, official Match ID and team identity. A retrospective PRE owns only
source/provenance details from the later reconstruction. The UI now resolves
main match labels through `MatchDisplayFormatter`, so the Official
Intelligence dropdown and selected-record header are generated from
structured canonical fields at render time. Source opponents such as Santa
Cruz can appear only in technical provenance, never in the primary Torres
title.

When no official PRE exists, Official Intelligence may use
`record.retrospective_pre` as the effective PRE for display and comparison,
but it labels it as retrospective and preserves the visible limitation. This
does not relax normal official PRE/POST Match ID rules: only the explicitly
linked retrospective simulation is allowed to differ from POST.

Saving a historical match into Weekly Planner now requires a match date. The
destination training cycle is resolved from that match date using the existing
Sunday-Saturday training-cycle calendar. The current computer date is not a
fallback for historical records.

### HF-08: one active record owns official evidence

POST import and replacement now respect the active Match Record. If the manager
is viewing/editing Torres, the pasted POST is attached to Torres or rejected by
Torres' own replacement/mismatch rules; another record with the pasted Match ID
does not steal selection or trigger a replacement prompt for the wrong record.
Official PRE plus POST still requires matching Hattrick Match IDs. Retrospective
PRE plus POST does not compare against the retrospective source ID because that
ID belongs to the later simulation, not the historical match.

Saved Match editing also restores the opponent from structured identity. Missing
Opponent Manager entries are shown as saved snapshots and block analysis until
the opponent is restored or deliberately changed.
