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

HF-07 extends the same principle to Weekly Planner saves. `Guardar como
Partido 1/2` resolves the destination training cycle from the currently open
record's match date (or the current form's explicit match date for a new
record). If no date exists, the action is blocked with a user-facing message
instead of falling back to the current week.

HF-08 extends it to opponent selection and official POST import. Opening a
Saved Match clears stale opponent selection and restores the saved record's
canonical opponent through structured combo item data. If that opponent no
longer exists in Opponent Manager, a saved-snapshot entry is selected and
analysis is blocked rather than falling back to another opponent. When POST is
imported while editing a saved record, the active record owns the import and
replacement check.

HF-09 extends the same isolation rule to the visible analysis result itself.
The Match workspace has two explicit modes:

- `NEW_MATCH`: a fresh preparation draft, with a generated draft owner ID.
- `EDIT_SAVED_MATCH`: an editor for one canonical `HistoricalMatchSnapshot`.

`MatchAnalysisResult` now stores serializable ownership metadata:
`analysis_owner_type` and `analysis_owner_id`. The repository may still have a
single persisted "last result" file for startup restoration, but the controller
must treat that file as usable only when its owner matches the current workspace
mode. New Match never restores a saved match's Formation Board, comparison or
lineup. Saved Match edit never restores a New Match draft result, and it only
restores a saved result when the stored owner ID equals the selected
`snapshot_id`.

This closes the reported stale-owner bug where the upper form could show saved
match metadata while the lower analysis area still belonged to a previous new
match. Opening a saved match clears the lower workspace before conditional
restore; opening New Match resets to an empty result state. Navigation also
preserves context: selecting "New Match" starts a new draft, while editing from
Saved Matches opens the Match workspace without selecting the New Match nav
entry.

HF-10.3 extends that isolation to competition type. The preparation selector's
structured item data is the canonical workspace match type. Analyze reads that
value, validates it, stores it in `MatchAnalysisResult.match_type`, and all
subsequent saves compare the current workspace type against that result
provenance. Unknown or missing selector data blocks analysis instead of becoming
League by default.

The selected weekly slot is never a competition-type source. `Guardar como
Partido 1` and `Guardar como Partido 2` only identify the planner slot being
written; they do not imply League or Cup/Friendly. `WeeklyMatchRecord.
competition_type` is copied from the current analysis provenance once it still
matches the visible workspace selector.

Policy for metadata changes after analysis: changing competition type marks the
current analysis stale, marks the workspace dirty, and disables the weekly save
actions until reanalysis. HT Coach does not offer a "save anyway" override for
this mismatch because the saved Match Record, Formation Board, Weekly Planner
record and validation path must all refer to one synchronized competition type.

HF-10.4 makes the persisted Match Record follow the same rule. The active Match
workspace resolves one structured metadata snapshot before saving: opponent ID
and name, competition type, venue role, scheduled date, HT season/week when a
season calendar is configured, and the independent Weekly Training cycle ID.
`Guardar formación`, `Guardar cambios`, `Guardar como Partido 1` and `Guardar
como Partido 2` all read from that same snapshot instead of reconstructing
metadata from labels, slots or stale analysis cache.

When saving an unsaved New Match, the controller validates that opponent,
competition type, venue role and scheduled date are present, creates one
canonical `HistoricalMatchSnapshot`, persists the lineup and metadata on that
same record, switches the workspace into saved-edit mode, and emits
`match_records_changed`. Reopening that record restores the same controls. Saved
Matches renders its visible title through `MatchDisplayFormatter`; the stored
`opponent_name` remains only the canonical rival name, never a title such as
`Hit'em up - Santa Cruz Club`.

HF-10.5 hardens the save workflow around one controller transaction:
`save_active_match_workspace`. `Guardar formacion`, `Guardar como Partido 1`
and `Guardar como Partido 2` all first persist the active workspace to the
canonical `HistoricalMatchSnapshot` and receive the saved record ID/revision.
Only after that do the weekly actions create or replace a `WeeklyMatchRecord`
with `linked_match_record_id` set to that same saved ID. A weekly-link failure
does not discard the canonical save or reset the Match page; the user remains
in saved-edit mode with the same board, metadata and results visible so the
weekly link can be retried.

Save actions are deliberately disabled until the workspace has valid metadata,
an analysis result, a recommended lineup and non-stale competition-type
provenance. Disabled buttons carry the reason as a tooltip. Save failures are
reported through the Match page and logged with the active record context
instead of being swallowed as a no-op.

HF-10.6 makes saved-match edit restore from the canonical record itself when
the transient last-analysis cache is missing or no longer belongs to the
record. `HistoricalMatchSnapshot.lineup` plus `tactical_setup` is enough to
display a usable restored Formation Board without rerunning optimizers. The
restored result is explicitly marked as `SAVED_MATCH` ownership for the active
record. The saved CSV path is kept in snapshot provenance and is loaded back
into the workspace on edit; if it cannot be loaded, the saved board remains
visible and the player count is cleared with an explicit warning instead of
showing a recent CSV label as if players were loaded.

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

## Formation Board local edits

The editable Formation Board uses `WorkspaceState.revision` plus stable tactical
slot ids to make local edits deterministic. Manual order controls capture the
selected `slot_id` and the current revision when the combo is built. The service
then validates that the same workspace revision is still active before applying
the order to the slot's current occupant.

Starter swaps preserve slot-owned orders where those orders remain valid. They do
not rerun `OrderOptimizer` or rewrite unrelated slots. If a moved player makes an
affected slot's current order invalid, only that affected slot is normalized to
`Normal`.

The view applies the model change first, emits the normal workspace-modified event
for controller recalculation, and schedules the visual rebuild for the next Qt
event-loop turn. This keeps PySide6 from deleting the active order combo while its
own `currentIndexChanged` signal is still executing.
