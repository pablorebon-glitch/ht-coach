# HT Coach UX Design System

Alpha 0.5.5 formalizes a lightweight PySide6 design system. It is intentionally small:
the goal is consistency and maintainability, not a separate UI framework.

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
- Shared table styling applies to Squad and Match tables.
- Source file indicator appears in page headers when a CSV path is selected.
- Full pytest suite remains green.

