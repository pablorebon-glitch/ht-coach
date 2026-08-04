# HT Season Calendar

Alpha 0.6.7 HF-02, Parts 11-13. Gives HT Coach a place to register when the
current Hattrick season begins, so it can derive Temporada HT / Semana
competitiva for a match date -- without ever guessing.

## Two calendars, never merged

- **Training cycle** (Sunday-Saturday, Thursday-21:00 processing cutoff):
  `engine/calendar/service.py`, from Alpha 0.6.5. Governs Weekly Planner.
- **HT competitive week** (Monday-Sunday, numbered inside the season):
  `engine/calendar/season_calendar.py`, from this hotfix. Governs Temporada
  HT / Semana competitiva display.

These stay structurally independent everywhere -- see
`engine/calendar/ht_season.py`'s own docstring (Alpha 0.6.6, Part 9) for the
original rationale.

## Still never guessed -- now deterministic once configured

HT Coach never *infers* a season/week from a date with no configuration. The
distinction this hotfix adds: once the user has explicitly told HT Coach an
anchor point ("season 95 starts 2026-07-27, 16 competitive weeks"), deriving
week numbers *from that known anchor* is deterministic arithmetic, not a
guess. Without a configured anchor, `resolve_season_context()` always
returns `confidence="unconfigured"` -- never a fabricated number. A date far
enough outside the configured season (more than one season-length away in
either direction) returns `confidence="unknown"` rather than compounding
uncertainty across guessed season boundaries.

## `SeasonCalendarConfig` (Part 11)

The persisted configuration is schema-versioned so future calendar changes
can migrate deliberately:

- `current_season_number`;
- `current_season_start_date`;
- `competitive_weeks`;
- `timezone`;
- `updated_at`;
- `schema_version`.

`SeasonCalendarConfig` still reads the older `season_number`,
`season_start_date` and `total_weeks` keys for backward compatibility, and
still writes those aliases while the app has existing user data in the wild.
`SeasonCalendarRepository.save()` stamps `updated_at` in UTC. The canonical
timezone shown in Settings is `America/Argentina/Buenos_Aires`; the older
`America/Buenos_Aires` value remains accepted as a compatibility alias.

Validation is intentionally user-facing rather than magical: season number
and competitive weeks must be positive, the timezone must be valid, and a
non-Monday start date produces a warning (`season_start_date_not_monday`)
instead of a silent correction.

## `resolve_season_context(match_date, config)` (Part 12)

Pure, Qt-independent, never calls `datetime.now()`/`date.today()` --
verified with a structural test that greps the module source for those
calls. Rules:

- Week 1 begins on the configured Monday; weeks are Monday-Sunday.
- A date within the configured season's span (`start` to
  `start + total_weeks*7 - 1`) resolves normally.
- A date up to one full season-length before or after the configured season
  resolves to the adjacent season (assuming the same configured length),
  marked `confidence="inferred_adjacent"` rather than `"configured"` -- an
  honest signal that this is one step removed from what the user actually
  typed in.
- Anything further out returns `confidence="unknown"`.

Verified against every one of the brief's own acceptance scenarios: the
configured Monday resolves to week 1, the following Sunday stays in week 1,
the next Monday becomes week 2, and a season configured for 16 weeks
resolves its own final week correctly.

## Recalculation (Part 12, continued)

`engine/calendar/season_recalculation.py` implements two explicitly distinct
behaviors:

- `recalculate_season_weeks(repository, config, force=False)` (the default,
  automatic path): only fills in records that have no season/week at all. A
  record that already has a value -- derived earlier or corrected by hand --
  is never touched.
- `recalculate_season_weeks(repository, config, force=True)` (Part 13's own
  "Recalcular partidos existentes" action): re-derives season/week for every
  record whose date resolves, overwriting whatever it currently has. This is
  a deliberate, explicit user choice.
- `preview_recalculation(repository, config)` is a read-only preview -- Part
  13's "show how many records will be updated before applying" -- verified
  to never mutate anything.

## Settings UI (Part 13)

Configuracion -> Calendario de temporada HT: a distinct card (never
presented as part of the training-cycle settings), with the brief's own
explanation text word-for-word, season number/start date/total weeks/
timezone fields, and Guardar/Cancelar/Recalcular partidos existentes
actions. "Recalcular" shows a confirmation naming exactly how many records
will change before applying, via `preview_recalculation()`.

HF-07 keeps the two calendars explicit in this UI: the competitive Hattrick
season week is Monday-Sunday, while the Weekly Planner training cycle stays
Sunday-Saturday.

## Wired into New Match (Part 14)

`MatchController` now accepts an optional `season_calendar_repository`; on
init and on every `match_date_changed` signal from the new date field, it
computes and shows both lines together -- "Temporada HT 95 / Semana
competitiva 2" (via `resolve_season_context()`) alongside "Ciclo de
entrenamiento ht-week-..." (via the existing training-cycle calendar,
unrelated and never merged). When no season is configured, shows the
brief's own exact wording ("Temporada HT: sin configurar") while still
showing the training cycle line -- never blocking match creation either
way. Verified end-to-end with both a configured and an unconfigured
calendar, and that the preview updates live as the date field changes.

## What's not yet built

Deriving `ht_season_number`/`ht_season_week` from the Season Calendar at the
point a new canonical Match Record is actually *created* (today
`find_or_create_provisional_record()` still needs the caller to pass
`season_number`/`season_week` explicitly -- the New Match preview shown to
the user isn't yet threaded into that call). And the deeper Part 3 fix this
calendar was meant to unblock (making `match_id` itself date-aware without
breaking the active-week assumptions elsewhere in
`weekly_training_service.py`) remains a larger, separate architectural
change for a future pass.
