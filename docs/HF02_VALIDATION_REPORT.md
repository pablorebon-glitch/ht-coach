# Alpha 0.6.7 HF-02 — Validation Report

Match Record Integrity, Season Calendar and Match UX Completion.
Consolidated per the brief's own Part 24 requirements.

## Root causes found and fixed

| # | Bug reported | Root cause | Fix |
|---|---|---|---|
| 1 | Deleting a Match Record could leave PRE/POST evidence behind | `MatchWorkspaceRepository`'s single "last analyzed result" cache stores official PRE data already merged into its sector comparisons; deletion never invalidated it | `clear_last_result()`, wired into `delete_saved_match()` when the cached result matches the deleted opponent |
| 2 | Individual player orders not editable | No order-editing control existed anywhere in the interactive `FormationBoard` UI, even though `WorkspaceService.set_manual_order()` (Alpha 0.6.6) was fully built and unused | Added a `QComboBox` order selector to the player inspector, wired to the existing `workspace_modified` recalculation pipeline |
| 3 | Weekly Match 1/2 used current week instead of match date | `record_first_match`/`record_second_match` always derived `match_id` from `state.active_week.week_id`, never from the match's own date; controller never passed the selected date through | Full fix, see below |
| 4 | Historical records with PRE/POST could lose date/type/season | `edit_record()` restored metadata to the form but only ever persisted the lineup back to the canonical record on save | `_persist_metadata_corrections_to_canonical_record()`, run whenever editing an existing record |
| 5 | Official Intelligence could render duplicated team names | Ad-hoc string formatting in the selector, no single source of truth | One central formatter used by the selector |
| 6 | Match history navigation/order inconsistent | Verified already correct from the original Alpha 0.6.7 sprint | No change needed; re-verified |
| 7 | Duplicate records for the same real match | Weaker duplicate-detection signal didn't consider venue, risking false positives on two-leg ties, and had no UI to resolve ambiguous conflicts | Added venue to the grouping key; built manual resolution and a Find Duplicates UI action |
| 8 | Home/Away/Neutral not stored | No selector existed; the underlying HomeAway enum was already present but unwired | Reused HomeAway; added the New Match selector, persisted on the canonical record |
| 9 | No Hattrick season configuration | Nothing existed to anchor which week a date belongs to | Built the full HT Season Calendar stack: config, deterministic resolution, recalculation, Settings UI |
| 10 | Ratings panel text-heavy, not Hattrick-like | Verbose sector labels; wrong card title | Rebuilt as a spatial 3x3 grid; retitled to Calificaciones |

## Part 3, in detail

Three layers, each found only after fixing the previous one:

1. The original bug: match_id always came from the active week, never the match's own date.
2. First fix attempt broke 6-9 pre-existing tests in test_weekly_training_planner.py -- not because the fix was wrong, but because those tests hardcoded fixture dates written assuming today would land near them; real wall-clock time had since moved past those dates. Fixed the tests to compute dates relative to the actual active week at run time, rather than hiding the problem by reverting the real fix.
3. A genuine edge case surfaced once those tests passed: the Thursday training-update cutoff means active_week.end_date marks that cutoff, not the calendar week's actual end. On a Friday/Saturday, today can fall before active_week.start_date. A hand-rolled boundary check got this wrong for the ordinary save-today's-match case. Fixed by reusing the exact same rollover-aware algorithm active_week itself was computed with.

Verified end-to-end through the real controller: a match dated 2026-07-26 resolves to match_id="2026-07-26:PLAYMAKING:first", distinct from the actual active week's own id, while an unmodified today still resolves consistently across the Thursday rollover boundary.

## Files changed (HF-02-specific)

New engine modules: engine/calendar/season_calendar.py, season_calendar_repository.py, season_recalculation.py; engine/history/match_deletion.py (extended), engine/history/duplicate_reconciliation.py (extended).

New services/UI: ht_coach_app/services/match_display_formatter.py, ht_coach_app/controllers/saved_matches_controller.py (extended), ht_coach_app/views/saved_matches_page.py (extended: Venue column, duplicate resolution dialogs).

Modified core files: ht_coach_app/controllers/match_controller.py, ht_coach_app/views/match_page.py, ht_coach_app/services/weekly_training_service.py, ht_coach_app/persistence/match_workspace_repository.py, ht_coach_app/views/settings_page.py.

New documentation: docs/HT_SEASON_CALENDAR.md. Updated: docs/UNIFIED_MATCH_WORKFLOW.md, CHANGELOG.md.

New test files: test_delete_evidence_cache_invalidation.py, test_editable_individual_orders.py, test_match_date_weekly_targeting.py, test_edit_metadata_correction.py, test_venue_role_and_display_formatter.py, test_saved_matches_venue_column.py, test_duplicate_resolution_ui.py, test_ht_season_calendar.py, test_new_match_season_preview.py, test_hf02_historical_and_retrospective.py, test_localization_completeness.py, plus updates to test_weekly_training_planner.py and test_pre_side_panel.py.

## Test totals

Full suite (excluding two known-slow files run separately and unaffected by this hotfix): 2115 passed, 0 failed, run in three batches due to tool time limits.

One test (test_responsive_layout.py::test_match_resize_cycle_preserves_workspace_and_scroll) is intermittently flaky under batched execution -- confirmed to pass consistently in isolation and on batch retry; pre-existing, unrelated to this hotfix.

Roughly 85 new tests added across this hotfix specifically for HF-02 scenarios, on top of the pre-existing suite.

## Migration results

engine/history/migration.py (from the original Alpha 0.6.7 sprint) continues to integrate correctly with this hotfix's changes -- verified explicitly that venue-aware duplicate detection still merges records sharing the same venue during migration, and correctly leaves venue-mismatched records (two-leg cup ties) unmerged.

## Manual acceptance (brief's own scenarios A-G)

- A. Delete/recreate: PASS -- verified end-to-end, no PRE/POST/Match ID resurrection.
- B. Orders: PASS -- verified against central defender/forward/goalkeeper scenarios on a real FormationBoard.
- C. Historical week: PASS -- match_id now correctly resolves to the training cycle containing the match's own date, verified through the real controller.
- D. Metadata: PASS -- Saved Matches shows real date/type/venue/season-week, never a fabricated Unknown.
- E. Season config: PASS -- week 1/week 2 derivation verified against the brief's own worked dates.
- F. Ratings card: PASS -- No cargadas before PRE, spatial grid of real values after (found and fixed a real gap: the card was silently staying empty instead).
- G. History: PASS -- central formatter verified to never produce duplicated name fragments.

## Known limitations

- Localization completeness (Part 19) verified with a permanent, automated test scanning every static t() call across the codebase, not just this hotfix's own additions. No gaps found.
- Full formation/lineup restoration on Edit remains best-effort (documented in the original Alpha 0.6.7 sprint's own closing notes) -- MatchWorkspaceRepository's single last-analyzed-result slot isn't yet keyed per canonical record.
- Coverage/exposure tracking continues to scope to the currently active training week by design (Squad page's this-week quick-edit semantics) -- a historical match's own weekly slot is correctly identified for saving/replacing, but does not appear in current-week coverage views, which is the intended behavior for a match that genuinely isn't in the current week.

## Validation commands run

python -m compileall ht_coach_app models engine tests -- clean.
git diff --check -- clean (only pre-existing CHANGELOG text matched loosely by the tool).

Full suite re-run in batches after every change in this hotfix; final confirmed total above.

## Git status

80 new (untracked) files, 213 modified files at time of this report. The majority of modified files are CRLF/LF artifacts from the zip-extraction environment (content identical, confirmed in earlier sessions of this workstream) rather than genuine content changes. No commits were made per the brief's own instruction.
