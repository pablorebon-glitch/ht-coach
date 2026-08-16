# Future Week Planning

Alpha 0.6.8 lets the manager prepare Weekly Training beyond the visible current
cycle without mixing cycles by training type alone.

## Weekly Planner

The Squad Weekly Planner exposes exactly three visible cycles:

- current cycle;
- current cycle + 1;
- current cycle + 2.

Each combo item stores structured `itemData`:

- `cycle_id`;
- `start_date`;
- `end_date`;
- `relative_offset`.

The visible date range is Sunday through Saturday. Coverage, records, suggested
lineups, empty states and delete/replace actions are scoped by the selected
`cycle_id`.

## Match Workspace

Match analysis resolves the training cycle from the selected scheduled date. A
future cup/friendly analysis therefore reads future weekly records and priorities
from that exact cycle, not from the active planner tab and not from a global Match
1/Match 2 lookup.

The result view stores only serializable metadata:

- `training_cycle_id`;
- `weekly_cycle_revision_used`;
- `training_context_timestamp`;
- `training_context_summary`;
- `training_context_stale`.

If the Weekly Planner changes after a result was analyzed, the Match workspace can
mark that context as stale and ask for re-analysis before saving training-sensitive
decisions.

## Guardrails

This feature does not alter optimizer formulas, rating calculations, probability
calculations, PRE/POST parsing or season-calendar formulas.
