# Match Decision Memory

Alpha 0.6.6 (partial) introduces `engine/lineup_memory/` -- comparing a
previously planned lineup against a new recommendation, classifying how
meaningful the difference actually is, and building a structured, evidence-
grounded explanation. Pure post-processing over already-computed
`FormationAnalysisResult` objects; never touches the optimizer, never
recomputes a rating.

## `MatchPlanRevision` (Part 2)

`compare_lineups(previous_result, new_result)` builds a `MatchPlanRevision`:
which slots changed player, which changed order only, whether the formation
or tactic changed, and the exact sector/possession/xG/win-probability deltas
between the two. `previous_result=None` (no previously saved plan) produces
an empty comparison rather than a crash. A formation change is reported as
`changed_formation` rather than attempting a slot-by-slot diff across
different shapes, which wouldn't be meaningful.

## `StabilityClassification` (Part 3)

`classify_stability(revision)` never changes a saved lineup for a marginal
optimization difference without saying so. Combines win-probability delta,
xG delta, and whether sectors moved in *opposite* directions (a genuine
trade-off, not a uniform improvement) into one of five classifications:
`CLEAR_IMPROVEMENT`, `MODERATE_IMPROVEMENT`, `MARGINAL_CHANGE`,
`EQUIVALENT`, `TRADE_OFF`. Every threshold lives on a typed, overridable
`StabilityThresholds` dataclass -- never a magic number in the classification
logic itself. `recommends_keeping_previous_lineup()` is true for
`EQUIVALENT`/`MARGINAL_CHANGE`, matching the brief's own worked example:
"the difference is marginal, maintaining the previous lineup is a valid
option."

## `ChangeExplanation` (Part 4)

`explain_revision(revision, classification)` replaces number-heavy change
explanations with a structured interpretation: for each changed slot, which
sector the change is meant to improve (`objective_key`), what it actually
improves and weakens (grounded entirely in the revision's own sector deltas
-- never invents a cause without a real delta crossing the significance
threshold), and whether it's a significant trade-off. The overall
`recommendation_key` reflects the stability classification. Verified against
the brief's own worked example character-for-character: replacing "Feliciano
Alvarez" with "Mauricio Bassedas" to improve midfield (+0.3) at the cost of
central defense (-0.2) classifies as `TRADE_OFF` and produces exactly the
objective/weakens pair the brief describes.

## Wiring

`MatchController._compute_and_show_plan_revision()` runs after a fresh
analysis completes (not after re-applying an Official PRE override on an
otherwise-unchanged lineup, which isn't a new recommendation to compare
against). It loads whatever was previously saved, computes the revision,
classification, and explanation, and calls `view.show_plan_revision(...)` if
the view supports it -- silently skipped otherwise, and never lets a
presentation-layer failure break the underlying analysis result from being
shown.

## Order preservation on manual replacement (Part 1)

Investigated `WorkspaceService.apply_replacement()`: slot and side were
already correctly preserved (via `dataclasses.replace()`, which only
overrides explicitly-listed fields), and `_apply_best_orders_to_slots()`
already avoids touching unrelated players' orders. The one real gap: there
was no way for the user to directly pick *any* valid order for a player
after a manual replacement -- only "apply order recommendation" (accepting a
suggestion) existed. `WorkspaceService.set_manual_order()` adds that entry
point, reusing the exact same `_board_with_order` primitive
`apply_order_recommendation` already uses -- not a second order system.

## Official ratings as primary context (Part 5)

Found a second, narrower bug alongside HF-02.2's root-cause fix:
`MatchPage._sector_ratings_comparable()` treated *any* comparison lacking
data -- including the optional indirect-set-pieces sectors, which frequently
have no data at all -- the same as a genuine scale mismatch. This made the
"Escalas distintas" warning appear even after Official PRE made the core
seven sectors fully comparable. Fixed by scoping the compatibility check to
comparisons that actually have both values present; a missing optional
sector is a data-availability question, not a scale-compatibility one.

## Removing the duplicated technical table (Part 6)

The main Match Intelligence section already delegates the raw sector-by-
sector table to a separate `rating_calibration` diagnostic section
(`_build_sector_rating_panel`) -- that separation existed before this
sprint. What was still duplicated: `_build_matchup_matrix()`'s own 6-row
numeric table (side/attack/defense/diff/classification) was rendered a
*second* time inside the main narrative panel, alongside the qualitative
highlights that already summarize the same advantages/risks in prose. The
matrix now renders only inside the technical/diagnostic section, appended
after the sector-rating table -- the main section keeps only the tactical
narrative (objective, key advantages, key risks, confidence), matching the
brief's own list of what belongs there.



## Weekly Planner navigation (Part 7)

`ht_coach_app/services/week_navigation.py`'s `build_week_navigation_context()`
supports exactly the three contexts the brief asks for -- previous, current,
next -- never unrestricted historical browsing (that belongs to Official
Match History instead). "Previous" is the most recently archived
`TrainingWeek`; "current" is `state.active_week`; "next" is always a
*preview* one training cycle ahead (nothing is persisted for it yet, since
that cycle hasn't started). Each context reports the canonical HT
training-cycle range, first/second match (matched by date range against
`state.match_records`, matching a saved plan even before the match is
played), and whether training priorities/coverage apply (only meaningful for
the current week; previous/next don't have a point-in-time snapshot of
priorities to show). Wired into the Weekly Planner tab with three buttons
(`week_nav_previous_button`/`current`/`next`) and a compact summary label --
navigating never touches the live editing view, which always reflects the
current week.

## Saving lineups into the Planner (Part 8)

Investigated `_save_as_first_match`/`_save_as_second_match` (Match) and
`record_first_match`/`record_second_match` (Weekly Planner service): the
core mechanics were already solid before this pass -- `add_match_record`
raises `duplicate_match_id` on a repeat save, which the controller already
catches and routes into a "Replace existing record?" confirmation
(`replace_first_match`/`replace_second_match`, updating the same record, never
duplicating), and `validate_match_status` already forces a future-dated match
to `PLANNED` rather than requiring it to be marked played first.

The one real gap: saving from Match never notified the Weekly Planner tab to
refresh, so a manager who saved a lineup and then switched to the Planner
would see stale data until something else happened to reload it.
`AppEvents.weekly_plan_saved` closes that gap -- emitted after each of the
four save/replace success paths in `MatchController`, and
`SquadController._refresh_weekly_training_after_external_save()` (cheap,
no-ops safely with no roster loaded) updates the Planner immediately whether
or not that tab is currently visible.

## What's not yet built (Parts 9-21)

This sprint's remaining scope -- the full `OfficialMatchRecord` lifecycle
(provisional/consolidated/complete status, retrospective PRE reconstruction,
season/week numbering, migration of existing standalone snapshots) -- is a
substantial sub-project on its own and remains for a future pass.
