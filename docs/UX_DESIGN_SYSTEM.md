# HT Coach UX Design System

Alpha 0.5.5 formalizes a lightweight PySide6 design system. It is intentionally small:
the goal is consistency and maintainability, not a separate UI framework.

## Previous Branch Review

The incomplete `feature/ux-product-polish` branch was inspected and treated as a
reference only. The reusable parts were reapplied on top of
`fix/opponent-ratings-input`:

- lightweight design-system modules;
- application stylesheet and focus styling;
- semantic `StatusBadge`, `Card`, `SectionHeader` and `EmptyState`;
- shared table configuration;
- compact page source indicators;
- Squad selected-tab presentation state;
- Transfer Planner priority badges;
- Match empty-state presentation;
- UX documentation and targeted smoke tests.

The previous Opponents-page changes were rewritten instead of copied directly because
the new base includes Alpha 0.5.4.3 Paste Ratings, Hattrick-order rating fields,
clipboard preview and locale-tolerant decimal input. Those behaviors remain owned by
the opponent input implementation. The polish layer only applies consistent panel
styling and localized visible labels around them.

No analytical, parser, calibration or optimizer changes were reused from the previous
branch.

## Architecture

Shared UI code lives in `ht_coach_app/ui/design_system/`.

- `spacing.py`: reusable spacing tokens.
- `typography.py`: text scale and emphasis tokens.
- `colors.py`: palette and semantic status colors.
- `metrics.py`: card radius, table row height and minimum control targets.
- `icons.py`: text/icon prefixes used by semantic badges.
- `styles.py`: application-wide stylesheet.
- `badges.py`: `StatusBadge` for semantic statuses.
- `cards.py`: `Card` for consistent panel hierarchy.
- `section_header.py`: `SectionHeader` for title, subtitle, status and action rows.
- `empty_state.py`: `EmptyState` for no-data, loading and recoverable-state panels.
- `tables.py`: shared table configuration.

## Semantic Status Policy

Statuses use the same vocabulary across modules:

- Positive: healthy, ready, available, strong alignment.
- Neutral: informational, stable, unspecified.
- Warning: watch, moderate risk, partial alignment, pending.
- Critical: critical risk, failed analysis, urgent structural issue.
- Unavailable: injured, blocked or unavailable.
- Unknown: missing, incomplete or insufficient data.

Clipboard import uses the same vocabulary: complete imports are positive, partial
imports are warning/informational, invalid clipboard content is critical only at the
recoverable input-error level, and not-directly-comparable rating scales remain neutral.

Color is never the only signal. `StatusBadge` pairs color with readable text and an
accessible description. Badges should be used for statuses that affect scanning, not for
every metric.

## Cards And Section Headers

Cards use consistent padding, border radius and selected/warning/critical variants.
Cards should frame repeated items, summaries and detail panels. Page sections should
remain unframed unless the user is comparing or selecting discrete items.

Section headers use a title, optional subtitle, optional status and optional contextual
action. They should replace ad hoc title rows in dense areas over time.

## Tables

Tables use shared row height, alternating row support, hidden vertical headers, explicit
selection behavior and interactive column sizing. Numeric columns should be right
aligned when possible; text columns remain left aligned. Sorting behavior remains owned
by the table item/model layer, not by click handlers.

## Empty, Loading And Error States

Empty states should include:

- concise title;
- short explanation;
- contextual next action when practical.

Loading states should say what is being calculated and should clear on success or
failure. They must not fake exact percentages.

Recoverable errors should show a user-facing message first. Technical detail can remain
available where an existing workflow supports it.

## Opponent Clipboard Workflow

The opponent editor keeps the Hattrick rating order from Alpha 0.5.4.3 and uses the
locale-tolerant rating inputs unchanged. The Paste Ratings action opens a localized
preview from the parser's structured result. The preview shows import status, team
metadata, ratings in canonical order and missing fields. Apply updates only parsed
fields; Cancel and parser failures preserve the form.

The preview does not display raw clipboard markup, does not persist clipboard metadata
and does not trigger Match analysis. Language switching can re-render visible labels
from structured state without changing parser semantics.

## Terminology

Preferred English terms:

- Current Available Squad
- Full Strength Squad
- Ideal XI
- Squad Identity
- Tactical Readiness
- Squad Health
- Evolution
- Transfer Planner
- Planning Horizon
- Succession Risk
- Internal Solution
- Recommended Profile

Preferred Spanish terms:

- Plantel disponible actual
- Plantel completo
- XI ideal
- Identidad del plantel
- Preparacion tactica
- Salud del plantel
- Evolucion
- Planificador de fichajes
- Horizonte de planificacion
- Riesgo de sucesion
- Solucion interna
- Perfil recomendado

## Accessibility

Alpha 0.5.5 improves accessible names for status badges, preserves text for major
actions, keeps tab navigation native, and adds visible focus styling through the shared
stylesheet. Icon-only actions must have a tooltip and accessible name.

Known limitations:

- The current app does not yet persist every splitter position.
- Some legacy explanatory labels are still plain text instead of expandable detail
  sections.
- PySide6 stylesheet support differs by platform, so visual focus treatment may vary.

## Responsive Desktop Assumptions

The UI targets normal desktop, smaller laptop and maximized desktop windows. It does not
target mobile. Dense areas should use scroll areas or splitters, avoid clipping primary
controls and keep player names visible.

## State Preservation

Persist analytical state separately from presentation state. Changing tabs, resizing,
expanding detail sections or switching language must not rerun analysis. Current
implementation preserves Squad selected tab, planner constraints, training focus,
availability mode and existing workspace settings through local JSON settings.

## Manual UX Checklist

Executed for Alpha 0.5.5:

- Minimum-size startup smoke test in offscreen mode.
- English and Spanish JSON catalog validation.
- No duplicate localization keys.
- Empty Match state renders with shared `EmptyState`.
- Squad tabs include Ideal XI, Players, Evolution and Transfer Planner.
- Transfer Planner priority urgency/action use text-bearing semantic badges.
- Opponents page uses localized visible labels.
- Opponent rating fields remain in Hattrick order and Paste Ratings remains reachable
  by keyboard.
- Clipboard preview supports Apply/Cancel and preserves existing form values on cancel
  or invalid input.
- Shared table styling applies to Squad and Match tables.
- Source file indicator appears in page headers when a CSV path is selected.
- Full pytest suite remains green.

