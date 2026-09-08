# Changelog

## Unreleased

### Changed

- Added Alpha 0.6.14 SP-01 competition-aware Match recommendation policy.
  Match now exposes three explicit sporting competition types: League, Cup and
  Friendly. League and Cup use the competitive policy (legal/available players,
  weekly training feasibility, then tactical strength). Friendly uses the
  rotation policy (legal/available players, weekly training feasibility,
  minimize avoidable Match 1 repetitions from the same training cycle, then
  tactical strength). Saved Match records persist and restore Cup and Friendly
  as distinct canonical values. No rating formulas, xG/WDL probabilities,
  official PRE/POST parsers, Weekly calendar rules, training slot semantics or
  manual Formation Board editing behavior changed.

### Fixed

- Fixed Alpha 0.6.13 HF-11 historical match metadata repair. Existing Saved
  Matches with official evidence but missing date, competition type or venue can
  now be edited and saved back onto the same canonical Match Record without
  rerunning analysis. Metadata repairs preserve Match ID, official PRE/POST,
  lineup and weekly links, refresh Saved Matches immediately, avoid silent
  League/today fallbacks, and include a read-only diagnostic for incomplete
  historical metadata. No ratings, xG/WDL, optimizer, training-rule,
  calibration, PRE/POST parser, calendar-calculation, recommendation identity or
  Formation Board logic changed.

- Fixed Alpha 0.6.13 HF-10 Match date field click handling. The internal
  QDateEdit text editor now treats normal left-clicks as calendar-open actions,
  so clicking either the visible date text or the arrow opens the popup without
  moving the text cursor or changing the selected date. Wheel protection,
  current/saved month behavior and all calendar calculations are unchanged.

- Fixed Alpha 0.6.13 HF-09 recommendation display, training constraint
  enforcement and match-date UX. Match recommendation labels continue to use the
  stable coach `recommendation_id` after manual Formation Board edits, the
  training-constrained optimizer now ranks slot-class-valid formations ahead of
  conflicted stronger alternatives when Required 50%/100% constraints are active,
  and clicking anywhere in the match-date field opens the calendar without
  changing the saved date. No rating, xG, probability, calibration, PRE/POST
  parser, calendar-calculation, packaging or legal-order logic changed.

- Fixed Alpha 0.6.13 HF-08 recommendation mutation in the live Match UI.
  Decision Lab summaries, comparison rows and Formation Board labels now derive
  "Recommended" from the stable coach `recommendation_id` instead of stale
  Decision Lab payloads, list position or transient `is_recommended` flags from
  manual workspace reevaluation. Manual player swaps can update the current XI
  evaluation without relabeling the original coach recommendation. No rating,
  xG, probability, calibration, PRE/POST parser, training-rule, calendar,
  packaging or legal-order logic changed.

- Fixed Alpha 0.6.13 HF-07 recommendation state integrity. Match results now
  persist a stable coach `recommendation_id`, manual workspace reevaluation
  refreshes only the visible XI evaluation, and save/PRE refresh paths no longer
  promote the currently visible formation to "Recommended". Runtime tracing now
  emits `ILLEGAL_RECOMMENDATION_MUTATION` if recommendation identity changes
  outside an explicit optimizer run. No rating, xG, probability, calibration,
  PRE/POST parser, training-rule, calendar, packaging or legal-order logic
  changed.

- Fixed Alpha 0.6.13 HF-06 training slot semantics after HF-05 clarified the
  wrong minute-target interpretation. Required 100% now means a full-training
  position class, Required 50% means a half-training position class, and the
  training-constrained optimizer satisfies those slot classes before tactical
  ranking when a feasible lineup exists. Weekly diagnostics distinguish actual
  training received from whether the requested training-plan slot class was
  respected. No rating, xG, probability, calibration, PRE/POST parser, calendar,
  formation persistence or legal-order logic changed.

- Fixed Alpha 0.6.13 HF-05 manual-edit stability and recommendation revisioning.
  Manual workspace edits now reevaluate the visible XI without replacing the
  last explicit coach recommendation, and match results track separate
  recommendation/manual-lineup revisions. No rating, xG, probability,
  calibration, PRE/POST parser or legal-order logic changed.

- Fixed Alpha 0.6.13 HF-04 runtime state trace and Match/Weekly cycle
  alignment. Match workspace metadata now derives `training_cycle_id` from the
  Weekly Training service, so saved matches and Weekly Planner records use the
  same cycle identifier. Added an opt-in JSONL runtime integrity trace
  (`HT_COACH_RUNTIME_TRACE=1`) for formation, saved-match, weekly-link and
  training-priority state transitions. No rating, xG, probability, calibration,
  PRE/POST parser or optimizer formulas changed.

- Fixed Alpha 0.6.13 HF-03 workspace authority and training priority freshness.
  Weekly Match 1/2 saves and linked weekly lineup refreshes now persist the
  currently visible Formation Board state instead of rebuilding from the cached
  optimizer recommendation. Match analysis now keeps the weekly training cycle
  revision it used, priority changes emit the planner-change event, and weekly
  coverage/plan diagnostics use the current normalized priority map so legacy
  100% records cannot override a current 50% setting. No training formulas,
  rating formulas, xG/WDL, calibration or parser logic changed.

- Fixed Alpha 0.6.13 HF-02 formation state integrity. Saved Match reopen and
  Official PRE/POST refresh now preserve the user-saved Formation Board state
  before falling back to cached optimizer recommendations, and individual-order
  legality now comes from one slot-aware policy shared by optimizer, workspace
  service and Formation Board. Central forward slots expose only Normal and
  Defensive orders. No rating, xG, probability or calibration formulas changed.

### Added

- Added Alpha 0.6.13 UX-03.1 Windows packaging hotfix. PyInstaller builds now
  install an HT Coach runtime hook that registers bundled PySide6 and shiboken6
  DLL/plugin directories before QtGui imports, making Explorer-style launches
  less dependent on inherited shell PATH state. No analytical, optimizer, rating,
  PRE/POST, Match, Opponent Manager or Weekly Planner behavior changed.

- Added Alpha 0.6.13 UX-03 Windows desktop packaging. A normal PyInstaller
  one-folder build now produces `dist\HT Coach\HT Coach.exe`, includes runtime
  resources/i18n, keeps portable mode gated by `portable.flag`, and adds an
  optional Desktop shortcut helper that targets the executable rather than
  Python or PowerShell. No optimizer, rating, probability, PRE/POST, Match,
  Opponent Manager, Weekly Planner or application-data semantics changed.

- Added Alpha 0.6.13 UX-02 Opponent Manager polish. The Opponents page now
  keeps list actions on the left and editing actions on the right, removes the
  visible Duplicate button, supports persisted manual up/down ordering with legacy
  opponents migrated safely, and keeps New Match opponent selection ordered by
  `created_at` recency instead of the manual manager order. No optimizer,
  rating, probability, PRE/POST, season-week or Weekly Planner logic changed.

- Added Alpha 0.6.13 UX-01 Match Preparation polish. The Rival selector now
  opens when clicking anywhere in the editable field, saved opponents carry a
  schema-compatible `created_at` timestamp for new entries, New Match lists
  timestamped opponents newest-first with legacy opponents kept afterward in a
  deterministic order, and the match-date calendar resets to the injected
  current month for fresh New Match while saved-match edits still open on their
  saved date. No analytical, optimizer, rating, PRE/POST, season-week or Weekly
  Planner logic changed.

- Added Alpha 0.6.12 bilateral Official POST support. The existing POST import
  action now auto-detects individual vs full-match POST exports, normalizes both
  into a unified `OfficialMatchPost`, preserves `official_post` as our-side
  compatibility data, enriches existing individual POST records with opponent
  actual ratings without duplicating Match Records, exposes a compact Rival Real
  section in Official Intelligence, and records POST validation evidence without
  changing rating, optimizer, xG or probability formulas.

- Added Alpha 0.6.11 rating-scale normalization foundations. Analytical ratings
  now carry explicit scale/source metadata, MatchEvaluator rejects explicit
  mixed-scale inputs, lineup/order/tactic optimization normalizes internal
  lineup ratings to an HT-compatible estimate before xG/WDL, objective traces
  include raw internal and normalized HT layers, and calibration storage/sample
  extraction supports future Official PRE rebuilds. Bootstrap v1 is
  low-confidence and sector-specific; it replaces the invalid 39.68-vs-5.75
  mixed-scale La Rocha evaluation without tuning probability formulas.

- Added Alpha 0.6.10 optimizer explainability foundations. Lineup evaluation now
  emits a serializable objective trace with sector ratings, possession/chance
  share, attacking and defensive matchup components, xG/o-xG, probabilities,
  training and availability components. Added a deterministic head-to-head
  lineup comparator, compact Pareto frontier support, La Rocha calibration
  fixture tests and Decision Lab payload wiring for recommended/alternative XI
  traces. The sprint keeps canonical TeamRater, tactic, xG and probability
  formulas unchanged; training is visible separately and only breaks close
  tactical ties in the comparator.

- Added Alpha 0.6.9 portable Windows distribution foundations. The app now has
  one canonical version source, detects `portable.flag`, routes portable user
  data to `data/`, logs to `logs/`, backups to `backups/`, resolves bundled
  resources independent of current working directory, copies roster CSV imports
  into `data/rosters/` with relative paths, adds manual data import with backup,
  and includes PyInstaller one-folder packaging scripts/docs. No optimizer,
  rating, probability, PRE/POST parser, Formation Board, Weekly Planner formula,
  season-calendar calculation, Match Intelligence or Club Advisor logic changed.

- Added Alpha 0.6.8 future Weekly Training planning. The Squad Weekly Planner
  now shows the current cycle plus the next two cycles, with structured
  `cycle_id` item data, cycle-scoped coverage and no accidental mouse-wheel
  changes on the week selector. Match analysis now resolves training context
  from the selected match date, persists the weekly revision used by the result
  and can mark a restored analysis stale when the Weekly Planner changes. No
  optimizer, rating, probability, PRE/POST parser or calendar formula code
  changed.

### Fixed

- Fixed Alpha 0.6.7 HF-10.7 duplicate saved-match record creation after
  importing Official PRE from a Saved Match editor. PRE/POST imports in
  `EDIT_SAVED_MATCH` now require the active canonical Match Record ID and attach
  evidence to that exact record instead of using the automatic import path that
  can create minimal official-evidence records. Explicit PRE imports now stamp
  the official Match ID/provenance onto the target record, repeated saves keep
  Weekly Planner links unchanged, and duplicate reconciliation can safely merge
  older partial PRE-only records with the single complete planned match for the
  same opponent while leaving ambiguous cases unresolved. No optimizer, rating,
  probability, PRE/POST parser, season-calendar, Formation Board order or weekly
  participation formula code changed.

- Fixed Alpha 0.6.7 HF-10.6 saved-match restoration and weekly-link continuity.
  Saved Match edit now restores competition type from canonical item data without
  converting missing values to Liga, restores venue from canonical `HomeAway`,
  reloads the persisted players CSV into the Match workspace, and can rebuild a
  visible Formation Board directly from the saved `HistoricalMatchSnapshot`
  lineup/tactical setup when the last-result cache is absent. Weekly saves from
  a Saved Match editor keep `EDIT_SAVED_MATCH`, preserve the active record ID,
  write Partido 1/2 against that same canonical record and leave the editor
  visible. Result enrichment now preserves match type and analysis ownership so
  Copa/Amistoso no longer turns into Liga through serialization. No optimizer,
  rating, probability, PRE/POST parser, Formation Board slot/order, season
  calendar or weekly participation formula code changed.

- Fixed Alpha 0.6.7 HF-10.5 Match save workflow isolation. `Guardar
  formacion`, `Guardar como Partido 1` and `Guardar como Partido 2` now share
  one canonical workspace save transaction before any Weekly Planner link is
  written. The transaction persists structured metadata plus lineup, switches
  New Match into saved-edit mode, keeps the board/results visible, emits saved
  match refresh events and reports actionable errors instead of silently
  swallowing persistence failures. Weekly saves now link to the same canonical
  Match Record ID and leave the workspace open; if the weekly link fails, the
  canonical save remains available for retry. Reopening saved records also
  reconciles old formatted opponent titles back to a clean managed opponent
  name when the match is unambiguous. No optimizer, rating, probability,
  PRE/POST parser, calendar, Formation Board order or weekly participation
  formula code changed.

- Fixed Alpha 0.6.7 HF-10.4 canonical Match metadata persistence when saving
  formations. `Guardar formación`, `Guardar cambios` and weekly save linking
  now read one structured workspace metadata snapshot for opponent identity,
  competition type, venue, scheduled date, HT season/week and training cycle.
  New Match formation saves create one complete canonical Match Record instead
  of a partial duplicate, then switch into saved-edit mode. Saved Matches now
  renders the title through `MatchDisplayFormatter`, keeps `opponent_name`
  canonical, formats saved dates for users, and preserves Copa/Amistoso,
  Local/Visitante/Neutral/Unknown and configured season/week on reopen. Added
  migration repair for malformed opponent names that contain formatted match
  identities such as `Hit'em up - Santa Cruz Club`. No optimizer, rating,
  probability, PRE/POST parser, evidence ownership, Formation Board order,
  calendar calculation or training participation formulas changed.

- Fixed Alpha 0.6.7 HF-10.3 Match competition-type synchronization. The Match
  workspace now treats the selector's structured item data as the canonical
  match type for analysis, saved Match Records, Formation Board weekly saves
  and `WeeklyMatchRecord.competition_type`. Invalid selector data blocks
  analysis instead of falling back to Liga. Changing the match type after an
  analysis marks that analysis stale and disables Guardar como Partido 1/2 until
  reanalysis, so weekly slot number no longer implies Liga or Copa/Amistoso. No
  optimizer, rating, probability, PRE/POST parser, Formation Board order,
  calendar or training participation formulas changed.

- Fixed Weekly Planner coverage isolation by training cycle. Coverage,
  participation provenance and `explain_weekly_player_state` now scope Match 1
  and Match 2 to the requested `cycle_id`, so records from older or future
  cycles can only appear in the diagnostic `Other cycles` section and always
  contribute zero minutes to the visible cycle. Linked weekly records with an
  invalid cycle are repaired from the canonical Match Record date when that is
  unambiguous; otherwise they are quarantined outside weekly coverage. Added
  regression coverage for the Bassedas cross-cycle leak, cycle switching,
  on-disk reload after repair and quarantine behavior. No optimizer, rating,
  probability, training percentage or PRE/POST parser formulas changed.

- Fixed Alpha 0.6.7 HF-10.1 stale Weekly Planner participation after lineup
  replacement. Coverage, plan generation and diagnostics now read a canonical
  weekly-record view that keeps at most one active Partido 1 and one active
  Partido 2 per training cycle, with duplicate/superseded slot records repaired
  on load. This closes the remaining source where an old Match 1 projection
  could still contribute a removed player such as Bassedas even after the linked
  record was replaced. Added `explain_weekly_player_state` diagnostics and
  regression coverage for disk reload, duplicate active Match 1 records,
  replacement, deletion, priority-only rows and table symbol semantics. Clarified
  that `○` means planned training from a lineup not yet counted as played. No
  training percentage rules, optimizers, ratings, probabilities, priorities or
  PRE/POST parsers changed.

- Fixed Alpha 0.6.7 HF-10 training participation integrity and Match
  preparation ordering. Weekly Training can now replace a linked saved match's
  current lineup by recomputing the complete weekly record from the final saved
  board, removing the previous record's exposure entries before inserting the
  new ones. This prevents removed players from continuing to count as played or
  trained after editing a saved match. Added participation provenance for
  diagnostics. Reordered Match preparation to Rival, Match Type, Venue, Match
  Date, Formations, formation actions, Analyze; Analyze is disabled until CSV,
  opponent and at least one formation are selected. The match date label now
  reads "Fecha del partido" / "Match date", and New Match defaults to the
  injected application calendar date instead of an accidental stale year. No
  training percentage rules, optimizer formulas, rating formulas, probability
  formulas or PRE/POST parsers changed.

- Fixed Alpha 0.6.7 HF-09 Match workspace isolation between New Match and
  Saved Match editing. Match analysis results now carry a serializable owner
  (`NEW_MATCH_DRAFT` or `SAVED_MATCH` plus ID), and the controller only
  restores, copies or saves a result when that owner matches the active
  workspace mode. Opening a saved match clears stale lower results before
  restoring only that record's own cached analysis; opening New Match creates a
  fresh draft context with no inherited Formation Board, comparison or lineup
  from the previous flow. Editing from Saved Matches keeps saved-match context
  instead of selecting the New Match navigation item. No optimizer, rating,
  probability, PRE/POST parser or tactical calculation code changed.

- Fixed Alpha 0.6.7 HF-08 official evidence ownership and saved-opponent
  restoration. POST imports from an actively selected historical record are now
  scoped to that record instead of being redirected by a global/latest Match ID
  lookup. Official PRE/POST mismatch rules remain strict, while retrospective
  PRE source IDs are not treated as real historical POST IDs. POST replacement
  updates only the active record and preserves retrospective PRE, opponent,
  date, competition, venue and lineup identity. Saved Match editing now restores
  opponent selector identity from structured combo data; if the opponent is no
  longer in Opponent Manager, Match shows a synthetic saved-opponent entry and
  blocks analysis instead of falling back to another rival. No optimizer,
  rating, probability or PRE/POST parser code changed.

- Fixed Alpha 0.6.7 HF-07 retrospective match identity, season calendar and
  historical Weekly Planner targeting. Retrospective PRE evidence is now read
  for Official Intelligence when no official PRE exists, but its source
  opponent and source Match ID never rename the canonical historical match.
  The Official Intelligence selector/header use canonical record metadata so
  Torres remains `Hit'em up vs. Torres Futbol Club` even when the supporting
  retrospective PRE was captured from Santa Cruz. Added safe migration repair
  for duplicated display strings and retrospective-source contamination, with
  ambiguous records reported instead of guessed. Season calendar persistence is
  schema-versioned with canonical fields, validation, timestamping and the
  `America/Argentina/Buenos_Aires` timezone option. Saving Match records as
  Weekly Planner Partido 1/2 now requires an actual match date and targets the
  Sunday-Saturday training cycle containing that historical date rather than
  silently falling back to the current week. No optimizer, rating, probability
  or PRE/POST parser formulas changed.

- Fixed Alpha 0.6.7 HF-06 page-only mouse-wheel behavior in the Match
  workspace: closed combo boxes, tab bars, date/spin controls and Formation
  Board selectors no longer change values from hover-wheel scrolling. Wheel
  input is redirected to the page scroll area where possible, while open combo
  popups and genuine inner scroll areas keep their normal scrolling behavior.
  Added regression coverage for Match inputs, formation/tactic/attitude
  selectors, the individual player-order selector, result tabs and scroll-limit
  safety. No analytical, optimizer, rating, probability, persistence or
  official-evidence parser behavior changed.

- Fixed Alpha 0.6.7 HF-05 Formation Board stability and slot integrity:
  manual starter swaps now preserve slot-owned valid orders instead of rerunning
  automatic order selection, manual order edits are applied by stable slot id plus
  workspace revision, the PySide6 order selector defers inspector rebuilds until
  after the combo signal returns to avoid access violations, and the Match
  Formation Board header now keeps actions reachable in restored windows. Added
  regression coverage for inner-midfield/winger swaps, slot-based order edits
  after swaps, and responsive Match layout behavior. No optimizer, rating,
  probability or official-evidence parser formulas changed.

- Fixed Alpha 0.6.7 HF-02 (Match Record Integrity, Season Calendar and
  Match UX Completion) -- a repair sprint over Alpha 0.6.7's own real-use
  regressions, found through manual verification. Root causes and fixes:
  deleting a Match Record left orphaned Official PRE data behind in a
  separate, un-invalidated cache (`MatchWorkspaceRepository`'s "last
  analyzed result" slot) -- added `clear_last_result()`, wired into
  deletion, verified with the brief's own exact 6-step scenario. Individual
  player orders had no editing control anywhere in the real Formation
  Board UI despite the underlying service already supporting it since
  Alpha 0.6.6 -- added an order selector to the player inspector, reusing
  the exact recalculation pipeline the existing replacement flow already
  used. Match date wasn't threaded from the New Match date field into
  Weekly Planner saves at all; fixed the controller wiring and the
  replace-confirmation dialog to name the actually-affected week -- an
  initial deeper fix (making the weekly match_id itself date-aware) broke
  9 pre-existing tests built around an "active week is the only identity"
  assumption throughout weekly_training_service.py, so that part was
  reverted and documented as a known, explicitly tested limitation rather
  than shipped broken. Metadata corrections (date/competition type/venue)
  made while editing a saved match were silently discarded -- only the
  lineup was ever persisted back; fixed to also persist match_context
  corrections onto the same canonical record. VenueRole reused the
  existing (but previously unwired) HomeAway enum rather than inventing a
  parallel one, added the New Match selector, and built one central
  match-display formatter (used by Official Intelligence's own selector)
  to reduce the risk of the reported duplicated-name-fragment bug. Added a
  Venue column to Saved Matches (was missing entirely) and added venue to
  the weaker duplicate-detection signal so a two-leg cup tie's home/away
  legs are never mistaken for the same duplicated record. Built the full
  HT Season Calendar stack (configuration, deterministic
  anchor-based resolution that still never guesses without a configured
  season, and recalculation that never overwrites manual corrections
  unless explicitly requested) and wired its live preview into New Match's
  date field. Found and fixed a genuine test-isolation bug of my own along
  the way: a new test that didn't isolate `WeeklyTrainingAppService`'s
  repository fell back to the shared, real user-data path, letting state
  leak across test runs and triggering a real, unmocked confirmation
  dialog that hung headless test execution. ~150 new/updated tests across
  the hotfix; full suite re-verified at 2093 passed / 0 failed. See
  docs/UNIFIED_MATCH_WORKFLOW.md and docs/HT_SEASON_CALENDAR.md.

- Fixed Alpha 0.6.7 (partial) Unified Match Workflow's own explicitly
  flagged bug: Official Match History's previous/next navigation
  (Alpha 0.6.6) sorted newest-first but treated raw array-index
  direction as the button semantics, so "Partido anterior" (should mean
  chronologically older) did nothing from the newest record and
  "Partido siguiente" (should mean newer) actually moved to an older
  one -- exactly backwards. Fixed the index arithmetic to match the
  labeled meaning, fixed deterministic ordering for records with an
  unknown date (always after dated ones, never randomly reordered
  between runs), and rewrote every affected test to assert on actual
  dates rather than array positions, per the brief's own explicit
  instruction -- the wrong code and the wrong test previously agreed
  with each other. Made the "COMPLETE requires official_post" status
  invariant an explicit, always-checked assertion rather than an
  implicit property of the derivation function's control flow, and
  verified provisional-identity collision safety against the brief's
  own numeric concatenation example. ~10 new/updated tests; full suite
  re-verified at 1877 passed / 0 failed. See
  docs/UNIFIED_MATCH_WORKFLOW.md. The larger scope of this sprint (New
  Match / Saved Matches screens, PRE import relocated beside the pitch,
  duplicate reconciliation) remains for a future pass.

### Added

- Added Alpha 0.6.6 Match Decision Memory, Weekly Planning Navigation and
  Official Match History. Manual lineup replacement was already correctly
  preserving slot/side and never resetting unrelated players' orders;
  `WorkspaceService.set_manual_order()` closed the one real gap (no way to
  directly pick any valid order after a replacement). New
  `engine/lineup_memory/` compares a previously planned lineup against a new
  recommendation, classifies how meaningful the difference actually is
  (CLEAR_IMPROVEMENT/MODERATE_IMPROVEMENT/MARGINAL_CHANGE/EQUIVALENT/
  TRADE_OFF, combining win-probability, xG, and whether sectors moved in
  opposite directions -- never one arbitrary player score), and builds a
  structured, evidence-grounded change explanation -- verified against the
  brief's own worked example (Bassedas/Alvarez, midfield gain vs. central-
  defense loss) character-for-character. Found and fixed a real scale-
  compatibility bug in Match's own sector-comparison check (optional
  indirect-set-piece sectors with no data were blocking otherwise-fully-
  comparable Official PRE vs. opponent comparisons) and removed a genuinely
  duplicated technical matchup table from the main Match Intelligence
  section, relocating it to the existing technical/diagnostic section.
  Weekly Planner gained previous/current/next week navigation (never
  unrestricted history -- that's what Official Match History is for) and
  immediate cross-page refresh when a lineup is saved from Match. Built the
  full `OfficialMatchRecord` foundation: a strict distinction between
  training cycles and Hattrick's own competitive season/week numbering
  (never computed from a date -- always explicit or unknown), typed record
  statuses always derived fresh from actual PRE/POST/retrospective-PRE
  evidence (never persisted separately), the progressive provisional ->
  consolidated -> completed record lifecycle (verified end-to-end to never
  duplicate a record), full official-match-history navigation wired into
  the real Match Intelligence page (season filter, previous/current/next,
  record identity header reproducing the brief's own layout example
  character-for-character), record editability rules, and the missed-PRE
  retrospective-simulation workflow (detection, save, and comparison
  labeling all engine-tested; the confirmation dialog widget itself is the
  one remaining UI piece). `HistoricalMatchSnapshot` was extended rather
  than duplicated as a parallel model, verified with a hand-written legacy
  payload to migrate without any data loss. ~150 new/updated tests across
  the whole sprint; full suite re-verified at 1864 passed / 0 failed. See
  docs/MATCH_DECISION_MEMORY.md and docs/OFFICIAL_MATCH_HISTORY.md.

- Added Alpha 0.6.5 Hattrick Weekly Cycle, Squad UX Simplification and
  Training Timeline: architecture-first, no new analytical engines.
  `engine/calendar/` is now the single canonical source of truth for "what
  HT week is this?" -- `HTWeekday`/`HTWeekState` typed enums, an
  `HT_DAY_ACTIVITY` table (the one place "Thursday means training" is
  defined), and `HTCalendarService` with `current_state()`,
  `next_transition()`, `days_until_training()/finances()/match()` and
  `week_snapshot()`. All eight `HTWeekState` values are reachable, mapped
  directly onto the day-to-activity table. Fixed the core bug this sprint
  targets in two separate places (`engine/weekly_training/training_week.py`
  and `weekly_training_service.py`'s `load_state()`): both used to compare
  bare `date` objects against the training-update date, so any moment on
  Thursday counted as "already processed" hours before the real 21:00
  server update -- both now respect the exact hour via
  `HTCalendarService.is_training_processed()` whenever a full `datetime` is
  available, falling back to the original date-only comparison only for
  backward compatibility with callers that never passed time-of-day
  information. Added pure, unimplemented `FinancialWeekSnapshot` and
  `YouthWeekSnapshot` contracts (every field defaults to `None`, never a
  fabricated zero) for a future Finance/Youth module. Verified the
  already-built Squad UX simplification (Role/State/Specialty filters only,
  positioned immediately above the player table), the official `Specialty`
  enum (all six Hattrick specialties, accent/case-insensitive parsing,
  full localization), the single week-context provider
  (`ht_week_context_provider.py`), and the compact "Current HT Week" header
  in the Weekly Planner -- all already wired correctly, confirmed end-to-end
  with real data. Swept Club Advisor and Match Intelligence for direct
  `datetime.now()`/`date.today()` calls (clean) and fixed the one remaining
  violation found. 33 new tests; full suite re-verified at 1708 passed / 0
  failed. See docs/HT_WEEK_CALENDAR.md for the full write-up.

### Fixed

- Fixed HF-02.2 Official Match Intelligence Integration and Advisor Modal
  Polish: found and fixed the root cause of Official PRE never reaching
  Match's tactical intelligence -- `MatchWorkspaceService._map_sector_comparisons`
  hardcoded `our_scale=SOURCE_HT_COACH_INTERNAL` unconditionally, so "our"
  side was always excluded from direct comparison even with a real Official
  PRE on the same Hattrick scale as the opponent estimate. Added a source-
  selection policy (Official PRE > calibrated internal, not yet confirmed >
  internal diagnostic) applied as a pure post-processing step over the
  recommended formation only -- the lineup optimizer, tactic optimizer, and
  every rating formula are completely untouched. Unified a second, independent
  left/right orientation mapping that had been duplicating the one in
  `sector_rating.py`. Added an `AppEvents.official_ratings_changed` signal so
  Match and Match Intelligence auto-refresh each other after an import from
  either page, with no restart or manual re-analysis. Added deterministic
  direction/magnitude interpretation and evidence-only conclusion generation
  for the PRE/POST comparison (verified against the brief's own worked example
  character-for-character), a responsive two-column PRE/POST layout, and a
  collapsed-by-default "Diagnóstico interno" section instead of always-visible
  "?" placeholder rows. Fixed two Club Advisor UI bugs: the drill-down modal's
  panel had no CSS rule of its own and inherited the overlay's translucent
  grey background instead of showing opaque white; and the Training drill-down
  showed player counts instead of the actual names, now derived directly from
  the Weekly Planner's own priority records. ~85 new/updated tests; full suite
  re-verified at 1656 passed / 0 failed. No optimizer, financial, or transfer-
  market logic was added. See docs/OFFICIAL_MATCH_INTELLIGENCE.md and
  docs/CLUB_ADVISOR.md for the full write-up.

### Added

- Added Alpha 0.6.4 UX Polish & Data Integrity stabilization. Official PRE
  and POST imports now keep independent parser/validator entry points because
  they are different Hattrick documents even though both feed the same internal
  snapshot model. PRE and POST are associated only by canonical Hattrick Match
  ID; when IDs differ, HT Coach shows a manual confirmation dialog instead of
  guessing, keeps the existing PRE unchanged on Back, and enables Apply only
  after both IDs match. Match Intelligence now emphasizes Official PRE,
  Official POST, Comparison and Conclusions, with HT Coach internal estimates
  demoted to supporting context. Club Advisor status text now always includes
  immediate causes when risks or warnings drive the global state, and its
  training card reads 100% / 50% / No training counts directly from Weekly
  Training Planner priority rows. Squad player filters were simplified to the
  practical Role, State and Specialty controls near the player table. The Club
  Advisor drill-down overlay was tightened into one elevated modal surface with
  explicit Explanation, Players involved, Reason, Impact and Review fields.
- Added Alpha 0.6.3 Advisor Grounding, Official POST Compatibility &
  Drill-down UX: not more rules, better-grounded ones. Official Match
  Intelligence gained automatic PRE/POST format detection and decimal
  comma/point normalization (calibration note: no real POST sample was
  available this sprint, so DETAILED_POST support is built from the brief's
  field list and verified against a synthetic fixture, pending a real sample).
  Club Advisor now separates structural club status (complete roster) from
  temporary availability (this week only, from the existing AvailabilityService)
  so a short-term injury is never conflated with a genuine depth gap; depth
  conclusions are formation-aware (reusing the training wizard's own
  formation-max helper) rather than assuming a flat replacement count; and a
  player's current position and future training project now coexist, fixing a
  real "Projects: 0" bug. Every risk now carries position, reason, impact,
  urgency, real affected-player names, and a review trigger instead of an
  abstract label; players-without-training and training-slot-pressure moved
  out of risks entirely into training-plan-specific warnings, since a position
  outside the active training's effect is often expected. Every squad count
  now exposes the actual player list behind it. Clicking any Club Advisor card
  opens a centered drill-down modal over a translucent overlay (closes via
  button, Escape, or outside click), and the headline project status now
  explains which dimension drove it rather than showing "Critical" with no
  reason. 39 new/updated tests; full suite re-verified at 1567 passed / 0
  failed. See docs/CLUB_ADVISOR.md and docs/OFFICIAL_MATCH_INTELLIGENCE.md.
- Added Alpha 0.6.2 Season-Aware Club Advisor: the core principle this sprint
  implements is that strategic need and operational urgency are independent
  dimensions -- a club can have HIGH defensive-depth need while simultaneously
  having LOW urgency to act on it, and the Advisor must never compute one from
  the other. Six new Qt-independent modules extend the existing Club Advisor
  package (no second engine): a fully optional `SeasonContext` that never
  fabricates missing values; `compute_urgency()` with documented, evidenced
  reducers/increasers and a per-need-tier floor that keeps a genuine need from
  ever collapsing to "nothing to look at"; `determine_action_type()`, the
  single place need and urgency combine into one recommended action;
  season-aware `RecommendationHorizon`s; need derivation from Club Advisor's
  already-computed depth/training/squad evidence (never recalculated); and an
  orchestrator producing separately-framed strategic and operational priority
  lists plus a preliminary, evidence-limited `PromotionReadiness` assessment
  (current-league dominance never implies promotion readiness by itself).
  Deliberate inaction ("maintain training, no signing currently required") is a
  first-class evidenced recommendation. The sprint's own worked example
  (central-defense depth: HIGH need, LOW urgency, MONITOR, review before
  promotion) and a synthetic 19-player regression fixture matching its
  described scenario are both reproduced exactly by the engine. Fully backward
  compatible: `generate_report()`'s new `season_context` argument is optional,
  `ClubAdvisorReport` gained four new optional fields, and every pre-existing
  Club Advisor test passes unchanged. UI: the existing Club Advisor page gained
  a compact, optional Season Plan card and Operational/Strategic
  Priorities/Promotion Readiness sections -- no new top-level page. 35 engine
  tests (all 12 required scenarios), 9 localization tests, 9 UI tests, 97%
  coverage on the new/changed code; full suite re-verified at 1520 passed / 0
  failed. See docs/CLUB_ADVISOR.md's "Need vs. Urgency" section for the full
  write-up.
- Added Alpha 0.6.1 Workflow Consolidation & Match Intelligence UI (UX-03): no
  new intelligence this sprint, just making HT Coach feel coherent.
  Training-type changes now show a confirmation dialog and a fully
  catalog-driven Training Priority Wizard
  (`engine/weekly_training/training_priority_policy.py`, verified against every
  worked example in the brief across all 12 training types, 41 parameterized
  tests). Match's official-summary import UI simplified to a single
  confirmation dialog; all ratings/metadata/comparison display moved to a new
  Match Intelligence page that reuses Alpha 0.5.9.0/UX-02's import service and
  formatting rather than duplicating it, and auto-refreshes on tab focus.
  Squad gained Role/Status/Training Fit filters and a scrollable, minimum-width
  detail panel. Found and fixed a genuine role-calibration bug behind "too many
  starters": positional rank was being computed against the entire roster
  instead of real peers, and current performance didn't account for how many
  players a position's formation slots actually call for -- fixing both dropped
  starter-tier roles from 63% to 47% of a real 19-player squad and correctly
  stopped a second goalkeeper from being classified as a starter. Also found
  and fixed a real localization-namespace collision: this sprint's first draft
  silently overwrote two keys of an existing, unrelated "Match Intelligence"
  (tactical focus) section inside Match's results panel, caught by an existing
  regression test; this sprint's content now lives under a distinct
  `official_match_intelligence.*` namespace. Full suite re-verified at 1467
  passed / 0 failed. See docs/ROADMAP.md's Alpha 0.6.1 entry and
  docs/OFFICIAL_MATCH_INTELLIGENCE.md for the full write-up.
- Added Alpha 0.6.0 Club Advisor Foundation: the first club-level intelligence
  layer, a new Qt-independent `engine/club_advisor` package that summarizes the
  current sporting project entirely from evidence already produced by Squad
  Intelligence and Training — never a new player-rating or scoring engine. A
  five-value project status is evaluated from three independent
  sub-assessments (training utilization, positional depth, squad composition)
  with the worst one capping the overall status, never a single blended score.
  An ordered priority catalog (8 types) never recommends a purchase, a
  specific player, or a transfer price. Independent strength/risk/warning
  detectors, each carrying evidence (warnings additionally carry an explicit
  reason). Five limitations (financial data, league comparison, transfer
  market, salary budget, promotion target) are always disclosed, since this
  sprint has no data source for any of them. A new "Club Advisor" navigation
  tab renders one concise card per section — no charts, no gauges, no overall
  score. `SquadIntelligenceContext` gained an additive `ages_by_position`
  field enabling genuine "future shortage" depth detection. Building against a
  real CSV caught and permanently fixed a pre-existing, unrelated flaky test
  in the training planner suite (a match-date safety guard tripped by real
  time having passed since the test was written). 62 new tests, 96% coverage
  on the new engine package; full suite re-verified at 1386 passed / 0 failed.
  See docs/CLUB_ADVISOR.md for the full write-up, including what's explicitly
  deferred (History integration, Transfer/Financial Planner, configurable
  Club DNA).
- Added Alpha 0.5.9.1 Squad Intelligence: a new Qt-independent
  `engine/squad_intelligence` package (15 modules) turns Squad into a
  player-management intelligence screen. For any current-roster player it
  produces a deterministic, evidenced classification — one of 11 recommended
  roles, one of 8 management statuses (deliberately no unconditional "sell"),
  five qualitative dimensions (current performance, training potential, training
  fit, salary efficiency, strategic value), strengths, risks, and a next
  milestone — with no raw overall score ever shown (a structural guarantee, not
  just a convention). Current performance reuses the existing `PlayerAnalyzer`
  positional ranking rather than a second rating engine; training fit reads the
  canonical Complete Training System via `rule_provider_for` rather than
  duplicating the training matrix. A documented rule ensures a very-high
  performer who's also an excellent-fit trainee resolves to KEY_STARTER over
  PRIMARY_TRAINEE (being currently irreplaceable outranks training status), with
  the training fit still fully visible in evidence either way.
  `ht_coach_app/services/squad_intelligence_service.py` bridges the current
  roster into the engine — building it against a real CSV caught a real bug
  (`PlayerAnalyzer.best_position()` returns a tuple, not a bare enum), now fixed
  and covered by a regression test. Full English/Spanish localization (151 keys,
  every enum member verified translated in both languages). UI: no new
  navigation page — the existing Squad player-selection flow now also renders a
  compact intelligence panel below the existing player detail, recalculating
  immediately when the active training type changes. 122 new tests, 96%
  coverage on the new engine package; full suite re-verified at 1320 passed / 0
  failed. See docs/SQUAD_INTELLIGENCE.md for the full write-up, including the
  documented role-conflict resolution and what's deferred to a future Club
  Advisor sprint.
- Added UX-02 Expose Complete Training and Official Match Import Workflows: an
  integration-only sprint (no new engine logic) wiring up two previously-built but
  hidden capabilities. Part A: the Weekly Training Planner's training-type
  selector (both the visible and legacy-compatibility combos) now populates from
  the canonical `TrainingType` catalog directly — all 12 types, localized labels,
  never a second hardcoded list — and changing the selection persists and
  recalculates immediately;
  `WeeklyTrainingAppService.set_active_training_type()` was added, fixing a real
  bug found while building this (switching training type mid-week would have
  silently orphaned already-recorded matches, since `TrainingWeek.week_id` embeds
  the training type). Part B: a single "Import Official Match Summary" action was
  added to Match (open, paste, confirm, no wizard), backed by a canonical
  tactic-alias catalog (`engine/history/official_ratings/tactic_catalog.py`,
  reused by the parser rather than duplicated) that resolves both this app's own
  translations and Hattrick's actual in-game wording to the same canonical
  `Tactic` enum; automatic Hattrick match-ID linking
  (`OfficialRatingImportService.import_and_link`) that links to exactly one
  matching record, creates an identifiable new one when none exists, and raises a
  conflict rather than guessing when more than one exists; and explicit PRE/POST
  replace-confirmation so a second paste is never silently reclassified. A
  prediction-vs-official comparison deliberately shows no numeric delta, since
  HT Coach's own predicted-rating scale isn't yet confirmed to align with
  Hattrick's official scale. 111 new tests; full suite re-verified at 1198 passed
  / 0 failed. See docs/ROADMAP.md's UX-02 entry and docs/OFFICIAL_RATING_WORKFLOW.md
  for the full write-up.
- Added Alpha 0.5.9.0 Official Hattrick Rating Workflow: a new Qt-independent
  `engine/history/official_ratings` package connects HT Coach with Hattrick's own
  "Copy Ratings" export. A tolerant English/Spanish parser extracts sector ratings,
  formation, tactic, team attitude and style from the pasted text without ever
  failing on unrecognized lines; validation separately rejects genuinely
  malformed/incomplete pastes. `HistoricalMatchSnapshot` gained two new optional
  fields, `official_pre` and `official_post`, coexisting with the existing
  `predictions` and `official_result` — purely additive, no schema migration
  needed. A deterministic three-way comparison (prediction vs. official PRE vs.
  official POST) and a diagnostic (not primary-UI) accuracy summary round out the
  engine layer. `OfficialRatingImportService` provides the "paste text, attach it
  to a match" app workflow, reusing the existing snapshot repository; imported
  official ratings are never regenerated or reinterpreted — "HT Coach proposes,
  Hattrick calculates, HT Coach learns." A pure `format_hattrick_notation`
  formatter renders the exact Hattrick-style ratings summary text but is not yet
  wired into the Match page. Calibrated against a real Copy Ratings paste from a
  live account (BBCode table format, not the originally assumed plain lines — see
  docs/ROADMAP.md for what that changed). 57 new tests, 97% coverage on the new
  modules; full suite re-verified at 1143 passed / 0 failed. See docs/OFFICIAL_RATING_WORKFLOW.md
  for the full workflow and docs/ROADMAP.md's Alpha 0.5.9.0 entry for what's
  shipped versus deferred.
- Added Alpha 0.5.8.5 Complete Training System (partial — first pass): a
  declarative training catalog (`engine/weekly_training/training_types.py`,
  `training_effects.py`, `training_definition.py`, `training_catalog.py`)
  generalizes the previously Playmaking-only weekly training system to all 12
  senior Hattrick training types, matching the full position/effect matrix with
  no `if training_type == ...` branching, including multi-skill training
  (Shooting trains Scoring and Set Pieces at different levels) and team-wide
  "every participant" effects (General, Set Pieces). `CatalogTrainingRules`
  implements the existing `TrainingRuleProvider` interface so every current
  caller (Match's Cup optimizer, weekly coverage) keeps working unchanged;
  `rule_provider_for()` now resolves all 12 types. Playmaking specifically keeps
  dispatching to the original, untouched `PlaymakingTrainingRules` class rather
  than the catalog — building the catalog surfaced a genuine, documented
  discrepancy (the matrix adds a "very small" effect for non-IM/winger
  participants that the original implementation never had), so real users'
  existing coverage numbers are not silently changed. 39 new tests, 100%
  coverage on the new modules; full suite re-verified at 1073 passed / 0 failed.
  Also added: English/Spanish localization for all 12 types, the four effect
  levels (Spanish wording pinned to the brief's exact text) and structured
  explanation templates; persistence migration tests proving legacy data
  defaults to Playmaking, explicit values are never overwritten, and an unknown
  future training type degrades safely with no data loss; `docs/PRODUCT_VISION.md`
  updated with this sprint's ten product principles.
  See docs/ROADMAP.md's Alpha 0.5.8.5 entry for what's shipped versus deferred
  (Match optimizer trade-off modes, weekly `PlayerTrainingResult` aggregation,
  and the Planner UI selector are not yet built).
- Fixed both previously-reported date-sensitive Weekly Planner test failures,
  root-caused rather than silenced: one was a missing `tzdata` package in the
  test environment (now declared in `requirements.txt`), not a code bug; the
  other was a test that implicitly built its "current week" from the real
  system clock and then asserted a rollover against a hardcoded date that only
  made sense in a specific wall-clock window — fixed by injecting an explicit
  reference date, with the root cause documented inline in the test.
- Added Alpha 0.5.8.4 Historical Insights Engine: a new Qt-independent
  `engine/history/insights` package turns Alpha 0.5.8.3 evolution results into
  deterministic, evidenced, confidence-scored insights via a small rule-per-concern
  catalog (sector, formation, lineup, individual-order, player-condition, tactical
  and prediction rules). Every explanatory insight carries at least one piece of
  evidence (enforced by the model itself); confidence follows a documented,
  deterministic policy (HIGH/MEDIUM/LOW/INSUFFICIENT_DATA); causal language is
  encoded as data (observed / associated with / likely contributor / possible
  contributor / insufficient evidence) rather than hand-written wording, so e.g.
  several inner midfielders switching to an Offensive order alongside an improved
  midfield rating is reported as a likely contributor, never a proven cause.
  Duplicate/near-duplicate insights are deterministically deduplicated and
  prioritized. A SummaryEngine builds a structured executive summary (comparison
  target, overall direction, main improvement, main decline, strongest likely
  contributor, confidence, limitation) by selecting among generated insights, never
  generating free text. `ht_coach_app/services/historical_insights_service.py` /
  `historical_insights_formatting.py` provide an app-facing bridge and
  presentation-only formatting, ready for a future Match History screen. No
  optimizer, rating engine, calibration, planner, snapshot schema, probability
  engine, midfield engine, Formation Board or Alpha 0.5.8.3 evolution calculation
  was changed; static-import and behavioral tests confirm insight generation never
  invokes FormationOptimizer/LineupOptimizer/TacticOptimizer/OrderOptimizer. The new
  package's test suite reaches 99% statement coverage. The Match History UI itself
  is intentionally not built in this sprint — see docs/ROADMAP.md for why.
- Added Alpha 0.5.8.3 Historical Evolution Engine: a new Qt-independent
  `engine/history/evolution` package computes pure deterministic evolution between
  two historical snapshots — sector deltas (midfield plus the six directional
  defense/attack sectors) with configurable-threshold trend classification, overall
  evolution (summed delta, average delta, best/worst sector, improved/declined/
  unchanged counts, overall trend), formation and tactical change detection, lineup
  evolution matched by stable player identity (never by row position, so reordered
  lineups compare correctly) reporting added/removed/kept players and per-player
  position/order/order-side/shirt-number changes, prediction evolution (expected
  goals, win/draw/loss probability, possession) and a documented `evolution_score`
  summary metric. A `HistoricalEvolutionEngine` service wraps the existing
  `PreviousMatchSelector` comparison policies (previous match, previous league,
  previous cup, previous friendly, same cohort, custom) without re-implementing
  selection. No optimizer, rating engine, calibration, planner, snapshot schema,
  probability engine, midfield engine or Formation Board code was changed; the new
  package's test suite reaches 100% statement coverage.
- Added Alpha 0.5.8.2 Historical Match Intelligence Foundation: a Qt-independent
  `engine/history` package now stores typed historical match snapshots with explicit
  schema versioning, planned-versus-played stages, canonical lineup orders and order
  sides, predicted and official ratings kept separate, deterministic JSON persistence,
  query/repository services, cohort classification, previous-match selection, a small
  developer CLI and an application service for creating snapshots from Match analysis
  without rerunning optimizers. Formation Board tactical left/right mirroring is now
  centralized so directional orders such as Michael Rushton's `Towards Wing / LEFT`
  are displayed consistently with Detailed XI and persisted snapshot semantics.
- Added Alpha 0.5.8.1 Real Match Calibration Dataset: a Qt-independent
  `engine/hattrick_ratings/calibration` workflow records played-match lineup
  snapshots, official Hattrick midfield ratings, validation quality, model-versioned
  observations, aggregate and segmented error metrics, JSON persistence,
  validation-dataset export/import, CLI commands, EN/ES localization keys, synthetic
  schema fixtures and full documentation without tuning `midfield-v1`.
- Added Alpha 0.5.8 Hattrick Midfield Rating Engine v1: a new Qt-independent
  `engine/hattrick_ratings` package estimates own-team midfield on Hattrick
  quarter-step units with explicit model versioning, form/stamina/context
  assumptions, confidence warnings, structured breakdowns, validation-provider
  integration, reference fixtures and a non-destructive midfield validation CLI.
- Added Alpha 0.5.7.4.2 Restored Window Geometry Fix: Match now refreshes
  geometry after resize and window-state changes, preserves the outer scroll
  position by ratio when restored dimensions change, restores Formation Board
  splitters proportionally instead of reusing maximized pixel widths, and keeps
  expanded accordion bodies visible after maximize/restore cycles.
- Added Alpha 0.5.7.4.1 Match Section Body Integration Fix: Decision Lab,
  Match Intelligence and Opponent Rating Calibration now use persistent body roots
  owned by the Match accordion, refresh updates their internal content without
  replacing the collapsible body, bounded internal scroll areas keep Intelligence and
  Calibration visible in restored windows, and expanded body hosts derive their
  minimum height from current content while collapsed hosts return to zero height.
- Added Alpha 0.5.7.4 Responsive Layout System Audit: Squad, Match and Weekly
  Planner now share a documented responsive workspace contract, splitters initialize
  from logical proportions instead of hardcoded pixel sizes, Formation Board minimums
  are less rigid for restored desktop windows, Weekly Planner explanations use bounded
  height instead of a fixed height, and responsive tests cover supported desktop
  resolutions, resize cycles, maximize/restore, pitch visibility and Match accordion
  stability.
- Added Alpha 0.5.7.3.3 Match Accordion Layout Reset: Match analysis sections now
  render as a strict accordion stack followed by the lineup workspace and one final
  stretch, expanded Decision Lab/Match Intelligence/Opponent Rating Calibration bodies
  use their natural content height, collapsed headers keep a clipped-free one-line
  summary, refresh while collapsed preserves section state, and repeated accordion
  cycles no longer leave stale blank space or push Match Analysis down the page.
- Added Alpha 0.5.7.3.2 Recorded Lineup Editing and Training Table Simplification:
  the Weekly Planner can reopen the recorded first-match lineup in the interactive
  Formation Board, save lineup changes back into the same match record without
  duplicating it, invalidate the generated second-match plan after edits, reduce the
  weekly player table to Player, Priority and Training Status, and keep Match
  collapsible sections stable through repeated toggles and result refreshes.
- Added Alpha 0.5.7.3.1 Planner Flow and Collapse Fixes: the Weekly Planner now lets
  the generated lineup area grow inside a natural vertical scroll flow, keeps Training
  Summary, Warnings and Explanations strictly below the pitch, filters the weekly table
  by stable visible priority roles, localizes planner warnings in EN/ES, and tightens
  the shared collapsible-section contract so collapsed bodies contribute zero height.
- Added Alpha 0.5.7.3 Workspace Layout Hardening and Training-Date Validation: the
  Weekly Planner result now keeps the shared Formation Board as a dedicated lineup
  workspace, shows a compact training summary instead of prominent sector deltas,
  keeps warnings and explanations in external bounded cards below the pitch, removes
  raw Python position tuple labels from the weekly table, validates past/today/future
  first-match dates before counting played exposure, and makes the Match analysis
  stack use only a final stretch after all collapsible sections.
- Added Alpha 0.5.7.2 Planner Execution Engine: Weekly Planner `Generate Plan`
  now builds a complete best-effort second-match lineup whenever a legal lineup
  exists, keeps ordinary priority conflicts as warnings/explanations instead of
  empty results, populates pitch, bench, orders, coverage and competitive cost, and
  lets `Use This Lineup` transfer the generated team into the editable Squad board.
- Added Alpha 0.5.7.1a Rebuild Collapsible Workspace Component: the Match analysis
  sections now use a simple header/body Qt layout with natural `sizeHint` behavior,
  no vertical expansion policy, no manual height animation or stale height clamps, and
  independent persisted state. Default Match result sections are Decision Lab collapsed,
  Match Intelligence collapsed, Opponent Rating Calibration collapsed and Match
  Analysis expanded.
- Added Alpha 0.5.7.1.1 Responsive Workspace Regression Fix: collapsed Match
  sections now release body height, Formation Board bench/details side panels can be
  collapsed in Match, Squad and Weekly Planner, Weekly Planner uses one unified player
  table with simplified priority labels and training-status symbols, and first-match
  records can be edited, replaced or deleted from the visible planner card.
- Added collapsible Match analysis sections for Decision Lab, Match Intelligence,
  Opponent Rating Calibration and Match Analysis, with reusable design-system
  component, independent persisted state, keyboard-accessible headers and EN/ES labels.
- Added Alpha 0.5.7 Weekly Training Lineup Planner with Playmaking priorities,
  Sunday-Wednesday-Thursday week handling, minute-aware exposure coverage, second-match
  lineup planning, assumed-versus-confirmed match records, competitive-cost reporting,
  persistent JSON state and EN/ES Squad-tab UI.
- Added Alpha 0.5.6.2.4 Match UI Stability and Incremental Refresh: Match refresh now
  reuses the result tab hierarchy, Formation Board, Pitch widget and player cards while
  preserving scroll, splitter, active-tab and selection state during automatic analysis
  updates.
- Added Alpha 0.5.6.2.3 Match Manual Intent and Viewport Stability: Match Workspace
  refresh now preserves manual player-slot assignments, keeps automatic order
  optimization scoped to assigned slots, protects against stale revision results and
  restores scroll/result-tab state after automatic refresh.
- Added Alpha 0.5.6.2.2 Initial Lineup Automatic Orders: Workspace creation now applies
  the canonical supported-order optimizer to all starters before saving the original
  optimized snapshot, so initial load, reload and Restore Optimized Lineup preserve the
  finalized non-Normal orders when they are optimal.
- Added Alpha 0.5.6.2.1 Squad Builder Manual Intent and Automatic Orders: manual
  slot assignments are treated as authoritative, affected players receive automatic
  supported individual orders, the Formation Board uses a Hattrick-oriented pitch
  orientation, and the primary Squad toolbar no longer shows Export.
- Added Alpha 0.5.6.2 Squad Builder Assisted Lineup with canonical click/drag lineup
  editing, starter-to-starter click swaps, manual lineup state, assisted position/order
  recommendations, explicit apply actions and EN/ES workspace localization.
- Added Alpha 0.5.6.1 Rating Validation Framework with typed validation fixtures,
  official-versus-predicted rating separation, completeness classification, JSON
  dataset loading, validation metrics, structured reports, a CLI smoke tool and the
  `docs/RATING_VALIDATION.md` guide.
- Added Alpha 0.5.6 Rating Engine Alignment Audit with typed rating scale concepts,
  Hattrick decimal descriptive mapping, candidate quarter-step conversion tests,
  developer diagnostics and `docs/RATING_ENGINE_ALIGNMENT.md`.
- Added Alpha 0.5.5.1 Decision Lab localization and Match Intelligence clarity:
  localized Decision Lab presentation/copy, explicit recommendation-support wording,
  and calibrated Match Intelligence display for non-comparable rating scales.
- Added Alpha 0.4.2.1 Compact Match Workspace with a responsive full-pitch view,
  horizontal board/inspector splitter, compact formation footer and internal Player
  Intelligence scrolling.
- Added Alpha 0.4.3 Interactive Workspace with an editable Workspace Lineup, immutable
  Recommended Lineup, replacement workflow and Reset Workspace baseline.
- Added `ht_coach_app/workspace` as a UI-independent workspace state and service layer
  for lineup edits, dirty state, replacement ranking and future undo/redo support.
- Added `docs/WORKSPACE.md` covering recommended versus workspace lineups, editing
  lifecycle, reset, recalculation and future Decision Delta/drag-and-drop milestones.
- Added fixed-lineup Workspace recalculation so the current Workspace Lineup can be
  evaluated without rerunning lineup optimization or replacing committed player changes.
- Added Evaluated Workspace status after successful fixed-lineup recalculation.
- Added Alpha 0.4.4 Drag & Drop Lineup Editing for the Formation Board, including
  starting-player slot swaps, dragged replacement candidates, Escape selection clearing
  and stale drag revision protection.
- Added Alpha 0.4.4.1 Integrated Bench Panel beside the Formation Board, with roster
  minus Workspace lineup derivation, bench-to-lineup and starter-to-bench exchange
  previews, keyboard replacement fallback and compact internally scrolling bench cards.
- Added Alpha 0.4.5 One-Click Workspace editing so valid click and drag lineup changes
  commit immediately, schedule automatic fixed-lineup recalculation, and keep Reset
  Workspace as the only global edit action.
- Added debounced Workspace recalculation with stale-result protection by Workspace
  revision.
- Added Player Intelligence contextual labels: `Why Recommended` for optimizer-selected
  players and `Workspace Impact` for manually inserted Workspace players.
- Added slot-specific Workspace score comparison wording with `in this slot` deltas.
- Added Alpha 0.4.6 Change Analysis, comparing the previous evaluated Workspace to the
  current evaluated Workspace after automatic recalculation.
- Added deterministic Change Analysis summaries for excellent trade-off, balanced
  improvement, risky change and net negative outcomes.
- Added English and Spanish localization catalogs under `resources/i18n`.
- Added `LocalizationService` with English fallback, missing-key safety and parameter
  substitution.
- Added `AppSettingsRepository` and a Settings language selector that persists the
  selected language.
- Added Alpha 0.4.7 Tactical Advisor with deterministic recommendation rules, impact
  scoring, confidence labels, localization and persisted verbosity.
- Added `engine/advisor` with independent lineup, formation, strength, weakness and
  balance rules plus impact-based ranking and duplicate removal.
- Added Alpha 0.4.7.1 Actionable Tactical Advisor card types: Action, Observation and
  Warning.
- Added centralized tactical matchup mapping for own attack versus opponent defense and
  opponent attack versus own defense.
- Added Advisor localization coverage for current and backward-compatible Tactical
  Advisor keys in English and Spanish.
- Added Alpha 0.4.8 Match Intelligence with deterministic matchup analysis, team
  profiles, opportunities, risks, exactly three tactical focuses, narrative summary and
  matchup matrix.
- Added `engine/match_intelligence` as a serializable interpretation layer over already
  evaluated Match Workspace results.
- Added Alpha 0.5.0 Squad Builder with an Ideal XI tab, Auto formation evaluation
  across the full catalog, Best Formations ranking, team profile, reused Formation
  Board and integrated Player Intelligence.
- Added Alpha 0.5.1 Squad Identity and Tactical Readiness, replacing the ambiguous
  Team Profile wording with descriptive squad identity, tactic capability readiness,
  formation affinity and main player contributors.
- Added Alpha 0.5.2 Squad Health and Availability with centralized injury parsing,
  current-available versus full-strength Squad Builder modes, health summary,
  availability impact, positional coverage, unavailable player explanations and Players
  table availability filtering.
- Added Alpha 0.5.2.1 Match Availability Integration so Match recommendations,
  Workspace recalculation, Bench, replacement candidates and Player Intelligence use
  Current Available Squad by default, while Full Strength simulation remains available
  with a clear warning.
- Added Alpha 0.5.3 Squad Evolution and Succession Planning with an Evolution tab,
  centralized age bands, planning horizons, succession map, dependency analysis,
  development candidates, training focus alignment, identity continuity and ranked
  planning risks.
- Added Alpha 0.5.4 Transfer Planner with profile-based recruitment priorities,
  planning constraints, internal-solution guidance, qualitative impact, no-action
  scenarios and Squad-tab integration.
- Added `engine/transfer_planner` as a deterministic planning layer over Squad
  Evolution outputs, explicitly excluding live market data, exact prices and exact
  future performance deltas.
- Added Alpha 0.5.4.2 Transfer Planner readability polish with semantic detail
  sections, centralized presentation mapping, localized list formatting and
  language-switch refresh without rerunning analysis.
- Added Alpha 0.5.4.3 opponent rating input improvements with Hattrick sector order,
  clipboard import preview, Spanish/English Hattrick table parsing and comma/point
  decimal entry support.
- Added Alpha 0.5.5 UX Consistency and Product Polish with a lightweight PySide6 design
  system, semantic badges, shared empty states, shared table configuration, localized
  Opponents copy and persisted Squad tab presentation state.
- Added `docs/UX_DESIGN_SYSTEM.md` documenting design tokens, semantic colors, badge
  rules, card patterns, empty/loading/error states, terminology, accessibility,
  responsive desktop assumptions and the manual UX checklist.
- Added Alpha 0.5.4.1 opponent rating calibration with explicit Hattrick decimal
  versus HT Coach internal rating scale labels, canonical sector matchups and
  persisted serializable Match result comparison view models.
- Added optional indirect defense and indirect attack fields to saved opponents while
  preserving the existing seven required sector ratings and JSON compatibility.
- Added centralized tactical workspace metrics for pitch ratio, card sizing, normalized
  formation spacing, splitter proportions and compact panel spacing.
- Added the Alpha 0.2 Squad Manager milestone for the PySide6 desktop app.
- Added roster CSV browsing, loading, reload, last-path persistence, and export of
  visible Squad rows.
- Added Squad search, minimum form/stamina filters, specialty filter, and position
  ranking filter.
- Added player detail and position analysis using existing engine analyzer APIs.
- Added Squad-to-Match roster path synchronization through application events.
- Added centralized user-facing position formatting with display names and abbreviations
  across Squad, Match, copied lineup text, and restored result view models.
- Added the full Alpha 0.2 formation catalog for Match analysis:
  2-5-3, 3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1, 5-2-3, 5-3-2 and 5-4-1.
- Added Select All, Clear All and Favorites controls to the PySide6 Match formation
  selector.
- Added the Alpha 0.2 Match Results UX milestone for the PySide6 Match Workspace.
- Added a prominent recommended-result summary with probabilities, possession and xG.
- Added formation comparison rows with deltas versus the recommended formation.
- Added a cleaner recommended XI table with number, side, position, player, order and
  order side.
- Added copy actions for match summary and recommended lineup.
- Added analysis metadata and last successful result restore from JSON view-model data.
- Added the Alpha 0.4 Formation Viewer milestone with a read-only PySide6 pitch board,
  compact player cards, formation switching, selection, and a player inspector.
- Added Alpha 0.4.2 Player Intelligence with deterministic player profiles,
  why-selected explanations, contribution bars, limitations and closest alternatives.
- Added `ht_coach_app/player_intelligence` as a UI-independent application layer.
- Added Player Intelligence documentation, including the explicit exclusion of chemistry
  and fabricated win-probability deltas.
- Added centralized formation-board layouts for all supported formations using normalized
  pitch coordinates.
- Added product vision and Formation Viewer documentation for the Calculate, Explain,
  Visualize, and Experiment product pillars.
- Added HT Coach Alpha 0.3 Decision Lab as a deterministic reasoning layer over Match
  analysis results.
- Added Decision Lab recommendation reasons, risks, tactical observations, confidence,
  sector matchup interpretation, optimization gain breakdown, and copy-ready text.
- Added persisted Decision Lab view-model data with backward-compatible restore.
- Added polished Decision Lab language for attacking channels, defensive vulnerabilities,
  xG interpretation bands, tactic-gain explanations, recommendation confidence, and
  copy-ready coaching summaries.

### Changed

- Squad Builder Assisted Lineup now removes visible Apply All / Apply Positions /
  Apply Orders confirmation controls. Valid edits apply immediately, automatic order
  optimization is bounded to affected slots, and the status badge uses neutral manual
  adjusted language instead of a permanent updating state.
- Formation Board click-to-click and drag-and-drop starter swaps now use the same
  `WorkspaceService` operation, including goalkeeper-slot protection and duplicate
  player prevention.
- Match analysis inputs now collapse after a successful or restored analysis and can be
  reopened or collapsed again through a persistent Analysis Setup toggle without
  rerunning optimization or clearing the current result.
- Simplified the visible Match summary to high-value context labels such as
  `Opponent:` and `Formations:`; CSV filename, player count, timestamps, copy buttons
  and the old Edit Analysis button were removed from that row.
- Match page content now scrolls vertically when needed so the Formation Board keeps a
  useful minimum pitch height.
- Corrected Formation Board pitch geometry so both goals are visible outside the field
  and all four corner arcs are anchored to pitch corners and curve inward.
- Match recommendation, metadata and Decision Lab presentation now use compact rows so
  the tactical workspace receives most of the available height.
- Formation player cards now elide long names according to their rendered width while
  preserving full names in tooltips; technical details are collapsed by default.
- The supported minimum desktop workspace is now 1280x720.
- Fixed Squad player table sorting so numeric columns such as TSI, salary, skills,
  selected position score and selected position rank sort numerically instead of
  lexically.
- Match analysis now reads supported formations from the centralized domain catalog
  instead of a hardcoded two-formation list.
- Existing users still default to the familiar 3-5-2 and 4-5-1 selections unless they
  already saved different formations.
- Improved Match page empty, loading, success and error states.
- Extended Match copy summary output with a concise Decision Lab section.
- Reduced Decision Lab duplication between reasons, risks, tactical observations, and
  sector matchup presentation.
- Kept optimization work on the existing background worker path.
- Match results now open on a Formation Board tab while preserving the Comparison and
  Detailed XI tabs.
- Copy Lineup output now follows pitch order: goalkeeper, defenders, midfielders and
  forwards from left to right.
- Formation Board selection now shows Player Intelligence when roster data is available
  and preserves a clean unavailable state for restored results without roster details.
- Formation Board now distinguishes Original Recommendation, Updating Analysis,
  Evaluated Workspace and failed analysis states while preserving the editable Workspace
  Lineup.
- Player Intelligence now focuses on explanation; primary replacement controls moved to
  the dedicated Bench panel while closest alternatives remain informational.
- Formation Board no longer exposes Apply, Cancel or manual Recalculate controls for
  Workspace edits.
- Workspace click and drag interactions now use the same service commit path and trigger
  fixed-lineup recalculation automatically.
- Reduced the Formation Board pitch footprint and preserved Match-page scroll position
  across selection, Workspace edits and automatic result refreshes.
- Match, shell, Workspace, Bench, Formation Board, Dashboard, Reports and Settings now
  retrieve migrated user-facing strings through the localization layer.
- Match results now show a Tactical Advisor panel that updates with normal analysis and
  automatic Workspace recalculation.
- Settings now persists Advisor verbosity as Simple or Detailed.
- Tactical Advisor now reserves actionable recommendations and impact badges for
  evaluated formation or Workspace lineup changes with measurable win-probability
  deltas.
- Tactical Advisor now presents weak sectors, low possession, attack concentration and
  defensive exposure as observations or warnings unless an evaluated change improves the
  result.
- Tactical Advisor ranking now prioritizes actions, caps them at three, keeps at most
  two context cards, and prevents generic strength notes from displacing actionable
  recommendations.
- Tactical Advisor localization now falls back to English and then to a safe generic
  message instead of rendering raw `advisor.*` keys.
- Improved Spanish Advisor copy for sector articles, exposed sectors and attack
  concentration observations.
- Match results now show a Match Intelligence panel between Decision Lab and Tactical
  Advisor.
- Tactical Advisor can consume Match Intelligence matchup view models when they are
  available.
- Transfer Planner presentation now localizes profile roles, target roles, positions,
  skills, specialties, formation relevance, impact dimensions, tradeoffs and no-action
  scenarios in English and Spanish.
- Transfer Planner detail output is now grouped into recommendation summary,
  recommended profile, why this transfer, expected impact, no-action scenario,
  alternative profiles and technical details.
- Transfer Planner priority rows now keep full localized values available as tooltips
  for dense table columns.
- Opponent ratings now display in canonical Hattrick order and manual inputs accept
  both decimal comma and decimal point while keeping internal values numeric.
- Missing localization keys and template parameters now fall back to localized safe
  text instead of showing technical placeholder text.

### Notes

- Optimization formulas, engine ratings, optimizers and probability calculations were not
  modified.
- Alpha 0.5.6.2.1 preserves the initial optimizer result as the restore snapshot and
  does not add training constraints, mandatory players, rest planning or new formulas.
- Assisted Lineup recommendations use existing internal contribution semantics only;
  they do not implement training constraints, mandatory players, Hattrick decimal
  conversion, rating estimation or optimizer scoring changes.
- Workspace edits are immediate view-model changes that are automatically evaluated as a
  fixed Workspace Lineup through existing calculation paths.
- Decision Lab explanations are deterministic and rule-based; no AI service, LLM,
  network dependency, or external API is used.
- Change Analysis uses only already calculated Match result view models and does not
  change engine, optimizer, probability, xG, rating, Decision Lab or Player Intelligence
  formulas.
- Tactical Advisor is informational only and never applies lineup, formation or tactical
  changes automatically.
- Actionable Tactical Advisor changes do not modify optimization formulas, player
  ratings, xG, probabilities, tactic behavior, Decision Lab, Player Intelligence or
  position weights.
- Match Intelligence does not modify TeamRater, optimizers, xG, probability formulas,
  rating formulas or Decision Lab.
- Opponent rating calibration does not introduce a conversion multiplier between
  Hattrick decimal ratings and HT Coach internal contribution ratings. Direct
  advantage labels are shown only when both ratings share the same source scale.
- Opponent clipboard import is presentation/data-entry only; it does not change rating
  formulas, sector calibration, cross-sector matchup mappings, optimizers or
  probability logic.
