# Official Match Intelligence

Alpha 0.6.1 (UX-03: Workflow Consolidation & Match Intelligence UI) moves every
official-rating analysis surface out of Match and into its own dedicated page,
so Match can stay focused on one job — preparing the next match.

## Why this page exists

Before this sprint, importing an official Hattrick summary inside Match also
displayed the parsed ratings, formation, tactic, match ID and timestamp directly
in Match's own panel. That mixed two different concerns: "prepare this match"
and "analyze what Hattrick officially calculated." This sprint separates them.

## What moved out of Match

Match keeps its "Import Official Summary" button and the underlying import
logic exactly as built in Alpha 0.5.9.0 / UX-02 — parsing, automatic Hattrick
match-ID linking, PRE/POST replace confirmation. What changed is what Match
*shows* afterward: a single confirmation dialog ("Official summary imported
successfully. [OK]") and nothing else. No ratings, no metadata, no timestamps,
no comparison are rendered inside Match anymore.

## What this page shows

- **Official PRE** / **Official POST**: the exact Hattrick-notation summary
  (`format_hattrick_notation`, unchanged since Alpha 0.5.9.0) for whichever
  captures exist on the most recently updated snapshot that has official data.
- **HT Coach Estimate**: the same diagnostic prediction-vs-official comparison
  built in Alpha 0.5.9.0/UX-02 (`compare_official_ratings`,
  `format_prediction_vs_official_comparison`). It still never shows a numeric
  delta -- see "Known limitation" below.
- **Sector Analysis**: the same seven-sector comparison, reformatted as a
  simple per-sector line.
- **Not Yet Available**: an honest, explicit note about what this page does
  *not* do yet (see below) — rather than silently omitting those sections.

## Import workflow

This page (unlike Match's single always-PRE button) lets the user explicitly
choose PRE or POST when importing
(`ht_coach_app/widgets/match_intelligence_import_dialog.py`), and supports
replacing either slot with the same explicit-confirmation semantics
`OfficialRatingImportService` already enforced. No new parsing or match-linking
logic was written for this — `ht_coach_app/services/match_intelligence_service.py`'s
`MatchIntelligenceAppService` is a thin bridge that reuses
`OfficialRatingImportService.import_and_link()` directly.

## Auto refresh

The page refreshes itself automatically whenever it becomes visible again
(`MatchIntelligencePage.showEvent` emits `refresh_requested`), so importing PRE
or POST — from this page or from Match — is reflected without a manual refresh
button. This also means an import made through Match's own button is picked up
here the next time this tab is opened, since both call sites share the same
underlying repository.

## Known limitation: scale compatibility

Same as Alpha 0.5.9.0: HT Coach's own predicted-rating scale is not yet
confirmed to align with Hattrick's official scale, so the HT Coach Estimate
section shows both raw values side by side with an explicit compatibility note,
never a numeric difference. See `ht_coach_app/services/official_rating_formatting.py`'s
`SCALES_CONFIRMED_COMPATIBLE` flag.

## Known limitation: opponent ratings and cross-match comparisons

The sprint brief describes an "Official Comparison" section (Official PRE vs.
Official Opponent Ratings) and cross-match historical comparisons / automatic
insights. **These are explicitly not implemented in this pass** — there is no
confirmed sample showing what an opponent's ratings export from Hattrick looks
like (the one real sample validated so far, from Alpha 0.5.9.0, is a single
team's own ratings block). Building speculative parsing logic for an unconfirmed
format would risk producing something that silently doesn't work against the
real thing. The page's "Not Yet Available" card states this plainly rather than
hiding the gap.

## A naming collision found and fixed while building this

Building this page initially localized its keys under a top-level
`match_intelligence.*` namespace — which turned out to already be in use by an
existing, unrelated feature: a collapsible "Match Intelligence" (tactical focus)
section inside Match's own results panel (`engine/match_intelligence`,
predating this sprint). The first draft of this work silently overwrote that
section's Spanish title and a `scale_limitation` key, caught by an existing
regression test (`test_english_and_spanish_headers_are_localized_without_raw_keys`)
rather than by inspection. The pre-existing `match_intelligence.*` namespace was
restored from git history exactly as it was, and this sprint's own content was
moved to a distinct `official_match_intelligence.*` namespace instead — matching
this document's own filename and avoiding any future collision with the older,
narrower "tactical focus" feature that happens to share a similar name.

## Responsibility boundaries

- Reuses `OfficialRatingImportService` entirely; no new parsing or match-linking
  logic exists in `match_intelligence_service.py`.
- Reuses `compare_official_ratings` / `format_prediction_vs_official_comparison`
  from Alpha 0.5.9.0/UX-02 rather than recomputing a comparison.
- Never recalculates an official value once imported (same discipline as every
  other History-adjacent module).
