# Official Match History

Alpha 0.6.6 begins the `OfficialMatchRecord` subsystem (Parts 9-21 of the
sprint). This document covers the foundational pieces built so far; it will
grow as the remaining parts (the full record lifecycle, provisional-record
creation flow, the history navigation UI, and migration) land.

## Two week concepts that must never merge (Part 9)

`engine/calendar/ht_season.py`'s `HTSeasonWeek` is deliberately separate from
`HTCalendarService`'s training-cycle concept (Alpha 0.6.5):

- **Training cycle**: Sunday-Saturday, with a Thursday-21:00 processing
  cutoff -- `HTCalendarService.training_week_id()`.
- **HT competitive season week**: Monday-Sunday, numbered inside the
  Hattrick season -- `HTSeasonWeek.season_number`/`season_week`.

HT Coach **never computes** `season_number`/`season_week` from a date --
`HTSeasonWeek` has no constructor path that accepts one, only explicit
values. Hattrick's season boundaries aren't reliable calendar arithmetic
(server-specific scheduling, cup weeks, season-length variation), so
guessing would produce a confidently wrong number, worse than showing
"unknown." `ht_coach_app/services/dual_week_formatting.py` always renders
both concepts as visually distinct lines, matching the brief's own worked
example:

```
Temporada HT 95
Semana competitiva 2
Ciclo de entrenamiento ht-week-2026-08-09
```

## Match record status (Part 12)

`engine/history/enums.py`'s `MatchRecordStatus` (PLANNED /
PRE_OFFICIAL_IMPORTED / PLAYED_POST_PENDING / COMPLETE / INCOMPLETE /
RETROSPECTIVE_PRE_AVAILABLE) is **never persisted on its own** --
`engine/history/match_record_status.py`'s `derive_match_record_status()`
always computes it fresh from whichever of official PRE / official POST /
retrospective PRE / match date are actually present, so the status can never
drift out of sync with the data it describes. All six statuses are verified
reachable from realistic combinations of that same evidence.

## Official vs. retrospective PRE (Part 16)

`OfficialRatingSnapshot` (`engine/history/official_ratings/models.py`)
gained additive fields -- `source_type`, `source_match_id`,
`linked_match_id`, `captured_after_match`, `confidence`, `limitation` --
never touching the parser itself (which still produces exactly the same
`SectorRatings`/formation/tactic shape it always has). These fields are
always set by the app layer at the point of import, based on whether the
manager confirms the capture belongs to the current match or is a later
reconstruction (Part 17's missed-PRE workflow). Fully backward compatible:
existing persisted snapshots without these keys default to
`captured_after_match=False` and empty strings, not a crash.

## The canonical record (Part 10)

`HistoricalMatchSnapshot` (`engine/history/models.py`) doubles as the
canonical `OfficialMatchRecord` -- extended with additive fields rather than
built as a parallel model, which gets Part 21's "migrate without loss"
requirement essentially for free (old persisted snapshots load fine with the
new fields defaulting sensibly). New: `retrospective_pre` (separate from
`official_pre`), `provisional_identity`, `training_cycle_id`,
`ht_season_number`, `ht_season_week`. Two computed properties, never
persisted directly: `season_week` (wraps the two HT-season fields as an
`HTSeasonWeek`) and `status` (Part 12's `MatchRecordStatus`, always derived
fresh from whatever official PRE/POST/retrospective-PRE/match-date evidence
the record actually has). `SCHEMA_VERSION` stays unchanged since the change
is purely additive.

## Progressive record creation (Part 11)

`engine/history/provisional_record.py` implements the exact flow the brief
describes, never creating a second record for the same match:

1. `find_or_create_provisional_record()` -- saved opponent + planned
   formation + match date/type -> a provisional record, identified by
   `compute_provisional_identity()` (season + week + date + opponent +
   competition type, case-insensitive on the opponent name). Calling this
   again for the same match returns the *same* record.
2. `consolidate_with_official_pre()` -- Official PRE provides the real Match
   ID; updates the same `snapshot_id`, never creates a new one.
3. `complete_with_official_post()` -- Official POST validates the Match ID
   (raising `MatchIdMismatchError` -- a new, narrowly-scoped error that
   never touches the existing PRE/POST Match ID mismatch dialog workflow --
   if it doesn't match what the record already has) and completes the
   record. Can also complete a record that never had an Official PRE at all
   (Part 17's missed-PRE workflow), landing on `INCOMPLETE` until a PRE
   (official or retrospective) is added.

Verified end-to-end: a full provisional -> consolidated -> completed cycle
never produces more than one stored record.

## History navigation and season filtering (Parts 13-14)

Unlike the Weekly Planner's restricted three-context navigation (Part 7),
Official Match History keeps the *full* available match history --
`engine/history/record_navigation.py`'s `list_records()` filters/sorts by
season number, `MatchRecordStatus`, and/or competition type (most recent
match date first); `available_seasons()` lists every distinct HT season
number actually present (records with an unknown season are never silently
grouped under a guessed one). `navigate_records()` moves previous/current/
next *within* whatever the active filter selected -- navigating "next" while
filtered to season 95 can never surface a season-94 record.

## Record editability (Part 15)

`engine/history/record_editability.py`: `is_normally_editable()` is true for
every status except `COMPLETE` -- a record with both official PRE and POST
present is completed history and read-only by default. Deliberately reuses
the same computed `status` property from Part 12, so editability can never
drift out of sync with the record's actual evidence. `requires_explicit_correction()`
is the inverse, named to match the brief's own "Allow an explicit Correct
record action" language -- there is no silent-edit path for completed
records anywhere in this policy.

## History navigation UI (Parts 13-14, 20)

`MatchIntelligencePage` now has a history header above the PRE/POST cards:
a season filter combo (always includes "All"), previous/current/next
navigation buttons, a record dropdown ("09/08 — CA Chaco — PRE oficial
importado", matching the brief's own worked example exactly), and a record
identity block reproducing Part 20's layout character-for-character:

```
Hit'em up vs. CA Chaco
Temporada HT 95
Semana competitiva 2
2026-08-09 · Liga
Estado: PRE oficial importado
Match ID: 770918226
```

`MatchIntelligenceAppService` gained thin wrappers
(`available_seasons()`/`history_records()`/`navigate_history()`) around the
Part 13-14 engine functions -- it already used the same
`HistoricalMatchRepository` these operate on, so no new repository or data
migration was needed. `MatchIntelligenceController` tracks the active season
filter and selected record as its own small piece of UI state; navigating
"next" is verified to never cross the active season filter boundary.
Backward compatible with the existing HF-02.2 auto-refresh behavior: when
nothing has been explicitly selected yet, it still falls back to
`latest_snapshot_with_official_data()`, so importing a fresh PRE/POST from
either page still shows up immediately.

## Missed-PRE workflow (Parts 17-18)

`engine/history/retrospective_pre.py`: `detect_retrospective_pre_candidate()`
identifies which already-played, PRE-less record a newly-imported PRE-shaped
capture is most likely a retrospective reconstruction for -- only when that
capture's own Hattrick match ID doesn't already belong to any known
snapshot (a normal import). Deliberately conservative: never offered for
still-planned/future matches (nothing to reconstruct retrospectively yet),
and never offered when a record already has PRE evidence (official or
retrospective).

`save_as_retrospective_simulation()` implements Part 17's own dialog outcome
("Guardar como simulación retrospectiva") -- attaches the capture as
`retrospective_pre`, storing its own `source_match_id` alongside the
record's `linked_match_id`, `captured_after_match=True`, and an optional
confidence/limitation. **Never touches `match_context`**: Part 18's rule
("the official record Match ID remains the POST/real match ID") is
structurally guaranteed, not just a convention. Along the way, fixed a real
gap in Part 11's own `complete_with_official_post()`: it never actually set
the record's official Match ID from the POST when completing a
provisional record -- found while verifying the retrospective flow
end-to-end.

## Retrospective comparison labeling (Part 19)

`ht_coach_app/services/retrospective_comparison_formatting.py`:
`comparison_label()` returns "PRE oficial vs. POST oficial" when a real
Official PRE exists, "Simulación retrospectiva vs. POST oficial" when only a
retrospective one does -- verified never to say "PRE oficial" in the
retrospective case. `retrospective_limitation_text()` is the brief's own
visible warning, word-for-word.

## Migration (Part 21)

Verified end-to-end with a hand-written legacy payload (no Part 9/10/16
fields at all, as if written by code from before this sprint): loads without
data loss (Match ID, dates, official PRE/POST all intact), gets a sensibly
derived status, defaults to an unknown season/week rather than guessing, and
can be re-saved afterward without corrupting anything.

## Missed-PRE dialog, connected (Part 17, closing piece)

`MatchIntelligenceController._offer_retrospective_pre_if_applicable()` hooks
into the real import flow: before treating a PRE-shaped paste as a normal
PRE, it parses the text (reusing `OfficialRatingImportService._parse_and_validate` --
never a second parser) and checks `detect_retrospective_pre_candidate()`. If
a candidate is found, `MatchIntelligencePage.confirm_retrospective_pre()`
shows the brief's own dialog word-for-word ("Este PRE fue generado para otro
Match ID y después del partido original... ¿Querés asociarlo como una
simulación retrospectiva?", buttons "Volver" / "Guardar como simulación
retrospectiva"). Confirming calls `save_as_retrospective_simulation()`
directly -- bypassing the normal `import_and_link` path entirely for this
case, since a retrospective capture must never become its own standalone
record. Declining does nothing at all. A normal PRE import (no candidate)
is completely unaffected -- verified the dialog method is never even called
in that case. Verified end-to-end through the real controller with a
realistic Copy Ratings paste: the retrospective PRE is attached, the
record's official Match ID stays exactly as the POST established it, and
no duplicate record is created.

With this, all 24 parts of the sprint have an engine-level implementation,
tests, and -- for every part with a user-facing surface -- real UI wiring.
