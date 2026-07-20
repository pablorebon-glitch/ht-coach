# Changelog

## Unreleased

### Added

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
