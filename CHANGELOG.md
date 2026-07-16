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
- Added the Alpha 0.2 Match Results UX milestone for the PySide6 Match Workspace.
- Added a prominent recommended-result summary with probabilities, possession and xG.
- Added formation comparison rows with deltas versus the recommended formation.
- Added a cleaner recommended XI table with number, side, position, player, order and
  order side.
- Added copy actions for match summary and recommended lineup.
- Added analysis metadata and last successful result restore from JSON view-model data.

### Changed

- Fixed Squad player table sorting so numeric columns such as TSI, salary, skills,
  selected position score and selected position rank sort numerically instead of
  lexically.
- Improved Match page empty, loading, success and error states.
- Kept optimization work on the existing background worker path.

### Notes

- Optimization formulas, engine ratings, optimizers and probability calculations were not
  modified.
