# Crash Diagnostics and Recovery

Alpha 0.6.7 HF-03, Parts 13-16.

## Crash log

`ht_coach_app/diagnostics/crash_reporter.py`. `install_crash_handler()` is
called once, from `ht_coach_app/app.py`'s own `run()`, replacing
`sys.excepthook`. On an unhandled exception:

1. Writes `logs/crashes/crash_<timestamp>.log` (UTC timestamp) with:
   timestamp, app version, Python version, platform, active page, active
   match_record_id, opponent, official Match ID, current action, source
   CSV, workspace dirty state, the full traceback, and the last 20
   application events.
2. Calls the caller's own on_crash callback, if provided -- app.py uses
   this to show the user-facing dialog.
3. Still calls the previous exception hook, so programmer errors are never
   hidden.

Never includes raw file contents -- only the CSV path -- and never raises
itself; a crash reporter that fails to write still prints the traceback to
stderr rather than losing it.

## Active context

`ht_coach_app/diagnostics/app_context.py` is a small, global, mutable
snapshot of "what is the application doing right now" -- updated by
controllers at key transitions (e.g. MatchController.edit_record() sets
active_page, active_match_record_id, opponent_name, official_match_id).
Read by the crash reporter at crash time; never otherwise consulted by
application logic.

## Event buffer

`ht_coach_app/diagnostics/event_buffer.py`. A 20-entry ring buffer.
record_event(action, match_record_id, outcome, detail) is the single entry
point controllers call after a Match action -- switch record, save
formation, import PRE/POST, delete record, and so on. Each entry only ever
stores an action name, a record ID, an outcome, and a caller-provided
detail string -- never raw personal data. Also feeds a
logging.Logger("ht_coach.events") for real-time structured logging,
independent of the crash path.

## User-facing crash message

`ht_coach_app/diagnostics/crash_dialog.py`. Shown from app.py's on_crash
callback. The brief's own exact wording -- "HT Coach encontro un error
inesperado. Se guardo un informe de diagnostico en: <path>" -- with
Copiar ruta / Cerrar buttons. Never raises itself.

The application does not attempt to continue in a corrupted workspace
after an unhandled exception; the default exception hook's own process
termination behavior is preserved.

## Recovery snapshots

`ht_coach_app/diagnostics/recovery_snapshot.py`. RecoverySnapshotStore
persists a lightweight snapshot (tactic, team attitude, formation name --
never a full board-state dump) to logs/recovery/<record_id>.json, one file
per record, always overwritten by the latest save. Saved before high-risk
actions:

- Switching away from a dirty workspace (edit_record(), saved before the
  unsaved-changes prompt itself, so a crash mid-prompt still has something
  to recover from).
- Importing official evidence (_import_official_ratings()).

Discarded automatically once the formation is genuinely saved
(_save_formation() calls store.discard(record_id) on success).

Never auto-restores -- load() is a pure read with no side effects; any
actual restoration requires an explicit decision from the person, matching
the brief's own Restaurar / Descartar requirement.

## What's not yet wired

The "on next launch, offer to restore if a newer snapshot exists" UI flow
(checking every logs/recovery/*.json file at startup and prompting) is not
yet connected to MainWindow's own startup sequence -- the storage layer
and the save points are built and tested, but the startup-time offer-restore
dialog itself remains for a future pass.

## HF-05 Formation Board crash

Alpha 0.6.7 HF-05 fixed a PySide6 access violation in the Formation Board order
selector. The crash was caused by rebuilding the player inspector immediately
from the order combo's `currentIndexChanged` handler, which cleared the inspector
and deleted/reparented widgets while the combo was still dispatching its signal.

The repaired flow blocks combo signals during population, applies the manual
order through the workspace service using stable slot identity, emits the normal
workspace-modified event, and defers the visual rebuild to the next Qt event-loop
turn. This keeps the crash fix in the UI layer and does not change optimizer or
rating behavior.
