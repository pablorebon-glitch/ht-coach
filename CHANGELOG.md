# Changelog

## Unreleased

### Added

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

### Notes

- Optimization formulas, engine ratings, optimizers and probability calculations were not
  modified.
- Decision Lab explanations are deterministic and rule-based; no AI service, LLM,
  network dependency, or external API is used.
