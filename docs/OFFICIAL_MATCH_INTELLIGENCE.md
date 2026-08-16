# Official Match Intelligence

## Alpha 0.6.12 Bilateral POST

Official Intelligence now accepts either an individual POST or a full-match
bilateral POST through the same import action. A bilateral POST is normalized to
`OfficialMatchPost`: the page continues using `our_team_post` for the main
PRE/POST comparison and optionally renders a compact **Rival real** section from
`opponent_team_post`.

The opponent actual side is evidence, not identity formatting. It must not
overwrite the prepared opponent snapshot or the canonical match title. See
`docs/BILATERAL_OFFICIAL_POST.md` for parser, enrichment and idempotence rules.

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

## PRE/POST format support (Alpha 0.6.3)

The parser now automatically detects which of two confirmed/expected shapes a
pasted "Copy Ratings" text uses (`engine/history/official_ratings/parser.py`'s
`detect_format()`):

- **COMPACT_PRE**: the BBCode `[table]` layout confirmed against a real
  pre-match sample in Alpha 0.5.9.0.
- **DETAILED_POST**: a plain labeled-line layout (no `[table]` block) matching
  the field list Hattrick's detailed post-match summary is documented to
  include (Midfield, Right/Central/Left Defense, Right/Central/Left Attack,
  Indirect Set Pieces, Game Plan, Average Ratings, Hidden Team Attitude,
  Playing Style).

**Calibration status: DETAILED_POST is not yet validated against a real
sample.** Unlike COMPACT_PRE (calibrated against an actual account paste in
Alpha 0.5.9.0), no real post-match "Copy Ratings" export has been provided as
of this sprint — the parser's POST support is built entirely from the field
names in this sprint's brief, using the same tolerant keyword-matching and
decimal-comma/point normalization the parser already had. It's been verified
against a synthetic fixture covering all listed fields
(`tests/test_official_rating_pre_post_formats.py`), but should be re-verified
against a real sample the next time one is available.

Detection itself doesn't change how parsing works underneath — the existing
tolerant line-based fallback already handled both shapes reasonably; `
detect_format()` mainly makes the distinction visible and testable
(`OfficialRatingSnapshot.detected_format`).

**Validation relaxed for POST.** A formation token is now only *required* for
COMPACT_PRE (where it's always present in the confirmed real sample).
DETAILED_POST may legitimately omit formation, team attitude, and other
PRE-only fields — their absence no longer fails an otherwise-usable import.

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

## HF-02.2: Official PRE as the Primary Rating Source

Root cause fixed this sprint: `MatchWorkspaceService._map_sector_comparisons`
always hardcoded `our_scale=SOURCE_HT_COACH_INTERNAL`, regardless of whether an
Official PRE capture existed for the match being analyzed. Since a comparison
is only ever marked `comparable` when `our_scale == opponent_scale`, "our"
side was *always* excluded from direct numeric comparison — even with a real
Official PRE on hand, on the exact same Hattrick scale as the opponent
estimate.

`engine/ratings/rating_source_policy.py`'s `select_our_ratings()` is the
single source-selection policy: **Official PRE > calibrated internal estimate
(not yet confirmed, so this tier never fires today) > internal diagnostic
estimate**. `MatchWorkspaceService.apply_official_pre_override()` applies this
as a pure post-processing step over an already-computed `MatchAnalysisResult`
— it never touches the lineup optimizer, the tactic optimizer, or any rating
formula. Only the *recommended* formation's ratings are substituted (Official
PRE was captured for whatever lineup was actually submitted, not every
candidate formation the optimizer explored); the top-level `match_intelligence`
result (tactical focuses, matchup classifications, opponent calibration) is
recomputed from that substitution using the exact same
`MatchIntelligenceEngine` unchanged.

**A second, smaller duplication was found and fixed alongside this**:
`engine/match_intelligence/matchup.py` maintained its own left/right
attack-to-defense pairing dictionaries, separate from
`engine/ratings/sector_rating.py`'s `MATCHUP_PAIRS` (the mapping the sector
comparison table already used). Both were consistent by coincidence — `matchup.py`
now derives its lookups from `MATCHUP_PAIRS` directly, so there is exactly one
centralized orientation mapping.

**Auto refresh** (already documented above) now also covers this override:
importing or correcting Official PRE re-applies `apply_official_pre_override`
to the last analysis result and calls `show_results()` again — no restart, no
manual re-analysis. A new `AppEvents.official_ratings_changed` signal lets
Match and Match Intelligence notify each other regardless of which page the
import happened on.

## HF-02.2: Interpreted PRE/POST Comparison and Conclusions

`engine/history/official_ratings/interpretation.py` classifies every sector's
PRE→POST change along two independent dimensions — direction
(`improved`/`stable`/`declined`) and magnitude
(`stable`/`small`/`moderate`/`large`) — using a typed, configurable
`InterpretationThresholds` (defaults: <0.25 stable, <0.50 small, <1.00
moderate, ≥1.00 large, matching the brief's own suggested defaults exactly).
`generate_conclusions()` then produces deterministic, evidence-only
observations: largest improvement, largest decline, stable sectors, an
overall improved/declined split, defensive/attacking/midfield trends (majority
direction across each sector group; a tie reads as stable rather than
guessing), and a missing-data limitation when some sectors couldn't be
compared. **Conclusions never claim a cause** (stamina, weather,
substitutions) — none of that evidence exists anywhere in this pipeline yet,
so it's never invented. A regression test pins that "PRE and POST are
associated by Match ID" alone is never the only output.

## HF-02.2: Layout and the Collapsed Internal Diagnostic

Official PRE and Official POST render in a responsive two-column row on the
Match Intelligence page, stacking vertically below a configurable width
breakpoint (720px) — both cards use identical structure so they're easy to
compare visually. The internal HT Coach estimate section (previously always
visible, always showing "?" placeholders since scales aren't confirmed
compatible) now collapses under "Diagnóstico interno" by default: a single
concise limitation note is shown, with the raw sector-by-sector values
available only on request (an expand/collapse toggle) for technical
inspection. Empty sector rows (neither a predicted nor an official value) are
never rendered.

## Responsibility boundaries

- Reuses `OfficialRatingImportService` entirely; no new parsing or match-linking
  logic exists in `match_intelligence_service.py`.
- Reuses `compare_official_ratings` / `format_prediction_vs_official_comparison`
  from Alpha 0.5.9.0/UX-02 rather than recomputing a comparison.
- Never recalculates an official value once imported (same discipline as every
  other History-adjacent module).
