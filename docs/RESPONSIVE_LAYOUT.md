# Responsive Layout System

Alpha 0.5.7.4 defines the shared desktop layout contract for HT Coach. The
application targets restored and maximized windows at:

- 1280x720
- 1366x768
- 1440x900
- 1600x900
- 1920x1080

The UI must not assume a maximized window. When vertical space is limited, the page
scrolls; the pitch, bench, player details and supplementary cards must not overlap.

## Workspace Contract

Squad, Match and Weekly Planner follow the same structure:

1. Header
2. Toolbar or setup controls
3. Workspace
4. Pitch
5. Bench
6. Player details
7. Supplementary cards
8. Bottom spacer

Supplementary cards include Training Summary, Warnings, Decision Lab, Match
Intelligence, Opponent Rating Calibration and analysis notes. They flow below the main
workspace and must not influence pitch geometry.

## Scroll Rules

Each page owns one main vertical scroll area when the full content may exceed the
viewport. Nested scroll areas are allowed only for bounded content such as bench lists,
player details, explanations and tables.

The main page scroll must preserve its position during analysis refreshes, workspace
updates, formation changes and collapse/expand actions where practical.

## Splitter Rules

Splitters start from logical proportions, not hardcoded pixel widths. Use
`set_splitter_proportions()` for initial sizing.

User resizing remains allowed. Refresh logic may preserve the user's current splitter
sizes inside a live workspace, but startup defaults should remain ratio-based.

When restoring from a different window width, raw splitter pixel sizes must not be
reapplied. Capture both sizes and ratios; reuse exact sizes only when the source and
target viewport widths are effectively unchanged, otherwise restore the same logical
proportions. This prevents maximized-window widths from becoming oversized restored
layouts.

## Size Policy Conventions

- Page shells use expanding policies.
- Headers and toolbars remain compact.
- Workspace containers use preferred vertical sizing inside a page scroll.
- Pitch widgets preserve aspect ratio and use readable minimum dimensions.
- Bench and player-details panels are bounded side panels.
- Tables expand naturally inside their parent panels.
- Collapsed accordion bodies contribute zero height.

## Formation Board

The Formation Board is the shared pitch workspace for Squad, Match and Weekly Planner.
It preserves pitch aspect ratio through the pitch geometry model. The pitch never
distorts to fill an incompatible rectangle; it centers the largest valid field inside
the available widget bounds.

If the window is too short, the surrounding page scrolls instead of clipping or
overlapping the pitch. Bench and player-details panels can be collapsed to recover
horizontal workspace.

## Match Accordion

Match result sections use a strict stack:

1. Decision Lab
2. Match Intelligence
3. Opponent Rating Calibration
4. Match Analysis
5. Lineup Workspace
6. Final stretch

The Lineup Workspace is not inside the Match Analysis accordion body. Collapsing Match
Analysis therefore cannot hide the pitch or leave stale workspace height inside the
accordion stack.

## Restored Window Geometry

Alpha 0.5.7.4.2 hardens Match restored-window behavior:

- resize, show and window-state changes schedule one deferred geometry refresh;
- stale deferred refreshes are ignored by a revision token;
- expanded Match section body layouts are invalidated before restoring viewport state;
- the outer Match scroll area remains the owner of vertical overflow;
- scroll restoration uses an absolute value for unchanged widths and a ratio when the
  restored viewport width changes;
- Formation Board splitters restore by ratio after maximize/restore or manual resize;
- maximized pixel geometry is not cached as restored layout state.

The supported restored validation sizes remain 1280x720, 1366x768, 1440x900 and
1600x900. Expanded bodies should remain visible at each size, collapsed bodies should
contribute zero height, and the Lineup Workspace should remain reachable by normal
page scrolling.

Alpha 0.5.7.4.3 adds initial restored-window stabilization for Match. Match may be
constructed while hidden inside the application `QStackedWidget`, so constructor-time
layout sizes are not authoritative. Stabilization runs only after the page is shown or
activated with a real scroll viewport. It performs at least two and at most three
queued event-loop passes, guarded by a generation token so older resize or activation
callbacks cannot apply stale geometry.

The stabilization pass may invalidate and activate the existing Match content,
results-stack and section layouts, refresh header height-for-width data, recompute
expanded body minimums, update the scroll content widget and clamp the outer scroll
position. It must not recreate widgets, toggle sections, recalculate analysis, change
formation, reset player selection or rebuild the page.

Startup geometry is considered valid when:

- collapsed sections show only their header and contribute no body height;
- expanded sections show a positive body height and content geometry;
- title and summary labels do not overlap;
- sections remain ordered without large gaps;
- the Lineup Workspace follows Match Analysis;
- the outer scrollbar range remains valid.

## Audit Notes

Alpha 0.5.7.4 removed the main responsive anti-patterns found during the audit:

- splitter startup sizes expressed as pixels;
- overly rigid Formation Board side-panel and pitch minimums;
- fixed Weekly Planner explanation height;
- workspace containers that forced maximized-window assumptions.

Remaining pixel constants are intentional readability bounds for cards, side panels,
table rows and pitch/player-card minimums.
