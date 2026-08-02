# Match Workspace State

Alpha 0.6.7 HF-03. What "which canonical Match Record does this workspace
represent" actually means, and the root cause it fixes.

## The bug this document exists to prevent from recurring

Reported: "A newly created match may inherit Official PRE data from another
record." Root cause: `MatchController._latest_official_pre_ratings()` and
`_update_pre_status_and_ratings_panel()` resolved Official PRE via
`service.latest_snapshot_with_official_data()` -- literally "whichever
canonical Match Record anywhere in the whole database was most recently
touched," with no regard for which match the workspace actually had open.
Analyzing a brand-new, completely unrelated match would silently inherit
another match's Official PRE the moment analysis ran, since that other
record simply happened to be the most recently updated one globally.

## `_current_workspace_record()` -- the single source of truth

`MatchController._current_workspace_record(snapshot_id_override=None)` is
the one place every workspace action resolves "which record is this."
Resolution order:

1. `snapshot_id_override`, when the caller already knows exactly which
   record was touched (e.g. `import_and_link()`'s own `ImportOutcome.
   snapshot`) -- authoritative, never re-derived.
2. `_editing_snapshot_id`, when a specific saved record is being edited.
3. The record matching the current opponent + date + competition type
   (the same identity `find_existing_or_conflicting_record()` already
   uses elsewhere), falling back to the currently displayed analysis
   result's own opponent name when the selector combo hasn't been
   separately populated.
4. `None` -- never a database-wide "most recent" fallback.

Both `_latest_official_pre_ratings()` (the PRE-application logic) and
`_update_pre_status_and_ratings_panel()` (the Calificaciones card) resolve
through this exact same function, so they can never disagree with each
other or with which match is truly open.

## Cross-controller event scoping

`AppEvents.official_ratings_changed` carries the touched record's own
`snapshot_id` (`Signal(str)`, not a bare `Signal()`). Any receiver that
acts on match-scoped data verifies the touched record matches what it
currently has open before reacting -- an event for an unrelated match is
silently ignored.

## Switching records: unsaved changes, recovery snapshots

`MatchController.edit_record()` is the switch point. Before actually
switching:

1. If the target is already the open record, nothing happens (not a
   "switch").
2. If the workspace is dirty (`FormationBoard.is_dirty()`), the person is
   prompted -- Cancelar / Descartar cambios / Guardar formación. A recovery
   snapshot is saved first regardless of the choice, so a crash mid-prompt
   still has something to recover from.
3. Only after that does the view model actually get cleared and reloaded
   from the newly selected record.

## What's not (yet) tracked in a formal `MatchWorkspaceState`

The brief's own suggested `MatchWorkspaceState` (match_record_id,
opponent_id, competition_type, venue_role, scheduled_date, source_csv,
lineups, tactic, orders, official evidence, dirty_flags, last_saved_at,
revision) is not a single formal dataclass in this codebase -- the
underlying data already lives across several existing places
(`HistoricalMatchSnapshot` for the canonical record, `WorkspaceState` for
the interactive board's own in-memory state, `MatchWorkspaceRepository`'s
"last analyzed result" cache). Introducing a single unifying type would be
a genuine architectural change beyond this hotfix's safe scope; the
isolation fix above solves the reported bug (leakage across records)
without requiring it.
