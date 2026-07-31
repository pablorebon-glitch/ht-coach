# The Hattrick Weekly Calendar

Alpha 0.6.5 introduces `engine/calendar/` as the single, canonical source of
truth for "what week is this?" -- every module that previously did its own
`datetime`/`date` arithmetic (or was about to need to) now reads from
`HTCalendarService` instead.

## Why an HT week isn't a real-world week

Hattrick's own weekly rhythm doesn't match a normal Monday-to-Sunday calendar
week, and it doesn't start on Monday either. It's anchored on the league
match, and everything else happens in a fixed sequence relative to it:

| Day | HT Activity |
|---|---|
| Sunday | League / Cup match |
| Monday | Recovery |
| Tuesday | Preparation |
| Wednesday | Friendly |
| Thursday | Training update (21:00 server) |
| Friday | Financial update |
| Saturday | Youth scout |

This table (`engine/calendar/enums.py`'s `HT_DAY_ACTIVITY`) is the single
place this mapping is defined. Nothing else in HT Coach hardcodes "Thursday
means training" again.

## The bug this sprint fixes: training weeks were rolling over too early

Before this sprint, two separate places computed "is this week's training
already processed?" by comparing bare `date` objects
(`date.today() >= training_update_date`). Since a `date` has no time-of-day,
*any* moment on Thursday -- including 00:01, hours before the real 21:00
server update -- counted as "already processed," causing the Weekly Planner
to roll over to a new training week too early.

`HTCalendarService.is_training_processed(now)` fixes this by comparing a full
`datetime` against the exact configured cutoff hour (21:00 by default,
`HTWeekScheduleConfig.training_hour`). `engine/weekly_training/training_week.py`
and `ht_coach_app/services/weekly_training_service.py`'s `load_state()` both
now delegate to it whenever a time-of-day-aware `datetime` is available --
falling back to the original coarser date-only comparison only when a caller
explicitly passes a bare `date` with no time information at all (kept for
backward compatibility with existing callers that never cared about the
hour).

## `HTWeekState`: the current phase of the week

`current_state()` maps directly onto the day-activity table above. Sunday,
Wednesday and Thursday are "milestone days" where the state flips from a
`PRE_` variant to the matching `POST_` variant exactly at that day's
configured processing hour. Monday, Tuesday, Friday and Saturday read as
fixed states for their entire day, matching their own activity: Monday
(Recovery) is `POST_LEAGUE_MATCH`, Tuesday (Preparation) is `PRE_FRIENDLY`,
Friday (Financial update) is `POST_FINANCIAL_UPDATE`, Saturday (Youth scout)
is `PRE_YOUTH_SCOUT`. There's no `PRE_FINANCIAL_UPDATE` or
`POST_YOUTH_SCOUT` -- those two events don't have a "getting ready for it"
phase the way a match, friendly or training session does.

## `HTWeekScheduleConfig`: never a hardcoded weekday again

Every processing hour is a field on a typed, overridable dataclass
(`engine/calendar/schedule.py`). The only hour this sprint's brief states
explicitly is training (21:00); the others are HT Coach's best-effort
approximation of a typical server schedule and are deliberately easy to
override per-league if real usage shows a different one, without touching
any call site.

## Single provider, no duplication

`ht_coach_app/services/ht_week_context_provider.py`'s `get_calendar_service()`
is the one shared `HTCalendarService` instance the whole app uses --
`current_week_snapshot()` is the one-call shortcut most callers actually want.
Weekly Planner, Club Advisor, Match Intelligence, Evolution and History all
read from this instead of constructing their own service or calling
`datetime.now()`/`date.today()` directly. `set_calendar_service()` is the
test/override hook that lets a test inject a fixed clock without patching a
module-level global by hand.

## What this sprint deliberately does NOT implement

Per the brief's own scope: `FinancialWeekSnapshot` and `YouthWeekSnapshot`
(`engine/calendar/models.py`) are pure, unimplemented *contracts* -- every
numeric field defaults to `None` (unknown), never a fabricated zero. No
Finance or Youth calculation exists anywhere in this sprint; a future module
consumes these shapes without HT Coach needing to redesign anything here.

## UI: the compact "Current HT Week" header

The Weekly Planner header (`ht_coach_app/services/ht_week_formatting.py`'s
`format_ht_week_status()`) renders all five weekly milestones as
Pending/Processed(-equivalent) pairs on one compact line -- never a large
widget, never a raw enum value or `snake_case` string leaking into the UI.
