from __future__ import annotations

from datetime import date, datetime, time, timedelta

from engine.calendar.enums import HTWeekState, HTWeekday
from engine.calendar.models import HTWeekSnapshot
from engine.calendar.schedule import DEFAULT_SCHEDULE

# HT's own week starts the day after the league match (Monday =
# Recovery) and ends with the match itself (Sunday) -- so "this HT
# week" is anchored on the most recent Sunday, not the ISO Monday.
# This offset table is Sunday-first, deliberately different from
# Python's native Monday-first `date.weekday()`.
_HT_WEEK_OFFSET = {
    HTWeekday.SUNDAY: 0,
    HTWeekday.MONDAY: 1,
    HTWeekday.TUESDAY: 2,
    HTWeekday.WEDNESDAY: 3,
    HTWeekday.THURSDAY: 4,
    HTWeekday.FRIDAY: 5,
    HTWeekday.SATURDAY: 6,
}

_WEEKDAY_FROM_PYTHON_INDEX = {
    0: HTWeekday.MONDAY,
    1: HTWeekday.TUESDAY,
    2: HTWeekday.WEDNESDAY,
    3: HTWeekday.THURSDAY,
    4: HTWeekday.FRIDAY,
    5: HTWeekday.SATURDAY,
    6: HTWeekday.SUNDAY,
}


def _most_recent_sunday(day: date) -> date:
    """The Sunday that starts `day`'s HT week -- today itself if `day`
    is a Sunday."""
    days_since_sunday = (day.weekday() + 1) % 7  # Python: Monday=0..Sunday=6
    return day - timedelta(days=days_since_sunday)


def _event_datetime(sunday_anchor: date, weekday: HTWeekday, hour: int) -> datetime:
    event_date = sunday_anchor + timedelta(days=_HT_WEEK_OFFSET[weekday])
    return datetime.combine(event_date, time(hour=hour))


class HTCalendarService:
    """The single source of truth for "what HT week is this?" -- every
    other module (Training, History, Finance, Advisor, Match
    Intelligence, Evolution) queries this instead of doing its own
    `datetime` arithmetic (Part 10 of this sprint). `now` is always an
    explicit, injectable parameter (or falls back to the configured
    clock) -- never read from the system clock silently, so every
    method here is deterministic and testable."""

    def __init__(self, schedule=None, clock=None):
        self._schedule = schedule or DEFAULT_SCHEDULE
        self._clock = clock or datetime.now

    def now(self) -> datetime:
        return self._clock()

    def current_weekday(self, now: datetime | None = None) -> HTWeekday:
        now = now or self.now()
        return _WEEKDAY_FROM_PYTHON_INDEX[now.weekday()]

    # -- Training timeline (Part 3: the core fix) --------------------

    def training_week_id(self, now: datetime | None = None) -> str:
        """A stable identifier for "which training cycle are we in" --
        changes precisely at Thursday 21:00 (or whatever the schedule
        says), never on a Monday. This is what the Weekly Planner reads
        instead of assuming a Monday rollover."""
        now = now or self.now()
        boundary = self._most_recent_training_boundary(now)
        return boundary.date().isoformat()

    def is_training_processed(self, now: datetime | None = None) -> bool:
        """Whether *this* HT week's training has already run. Before
        Thursday's processing time: still pending, and the active
        training week must keep showing the prior cycle's data -- this
        is exactly the condition the Weekly Planner needs to decide
        whether to roll over."""
        now = now or self.now()
        sunday_anchor = _most_recent_sunday(now.date())
        boundary = _event_datetime(
            sunday_anchor, self._schedule.training_weekday, self._schedule.training_hour
        )
        return now >= boundary

    def days_until_training(self, now: datetime | None = None) -> int:
        return self._days_until(self._schedule.training_weekday, self._schedule.training_hour, now)

    def days_until_finances(self, now: datetime | None = None) -> int:
        return self._days_until(self._schedule.financial_weekday, self._schedule.financial_hour, now)

    def days_until_match(self, now: datetime | None = None) -> int:
        return self._days_until(self._schedule.match_weekday, self._schedule.match_hour, now)

    # -- Week state ------------------------------------------------------

    def current_state(self, now: datetime | None = None) -> HTWeekState:
        """The current phase of the HT week, matching the day-to-
        activity table this sprint's brief itself defines: Monday
        (Recovery) reads as POST_LEAGUE_MATCH, Tuesday (Preparation) as
        PRE_FRIENDLY, Friday (Financial update) as
        POST_FINANCIAL_UPDATE, Saturday (Youth scout) as
        PRE_YOUTH_SCOUT. Sunday/Wednesday/Thursday are the three
        "milestone" days, where the state flips from PRE_ to POST_
        exactly at that day's configured processing hour."""
        now = now or self.now()
        weekday = self.current_weekday(now)
        sunday_anchor = _most_recent_sunday(now.date())

        if weekday == HTWeekday.SUNDAY:
            match_at = _event_datetime(
                sunday_anchor, self._schedule.match_weekday, self._schedule.match_hour
            )
            return HTWeekState.POST_LEAGUE_MATCH if now >= match_at else HTWeekState.PRE_LEAGUE_MATCH
        if weekday == HTWeekday.MONDAY:
            return HTWeekState.POST_LEAGUE_MATCH
        if weekday == HTWeekday.TUESDAY:
            return HTWeekState.PRE_FRIENDLY
        if weekday == HTWeekday.WEDNESDAY:
            friendly_at = _event_datetime(
                sunday_anchor, self._schedule.friendly_weekday, self._schedule.friendly_hour
            )
            return HTWeekState.POST_FRIENDLY if now >= friendly_at else HTWeekState.PRE_FRIENDLY
        if weekday == HTWeekday.THURSDAY:
            training_at = _event_datetime(
                sunday_anchor, self._schedule.training_weekday, self._schedule.training_hour
            )
            return HTWeekState.POST_TRAINING if now >= training_at else HTWeekState.PRE_TRAINING
        if weekday == HTWeekday.FRIDAY:
            return HTWeekState.POST_FINANCIAL_UPDATE
        return HTWeekState.PRE_YOUTH_SCOUT

    def next_transition(self, now: datetime | None = None) -> tuple[HTWeekState, datetime]:
        """The next milestone that will occur, and when."""
        now = now or self.now()
        sunday_anchor = _most_recent_sunday(now.date())
        candidates = [
            (HTWeekState.POST_LEAGUE_MATCH, _event_datetime(
                sunday_anchor, self._schedule.match_weekday, self._schedule.match_hour
            )),
            (HTWeekState.POST_FRIENDLY, _event_datetime(
                sunday_anchor, self._schedule.friendly_weekday, self._schedule.friendly_hour
            )),
            (HTWeekState.POST_TRAINING, _event_datetime(
                sunday_anchor, self._schedule.training_weekday, self._schedule.training_hour
            )),
            (HTWeekState.POST_FINANCIAL_UPDATE, _event_datetime(
                sunday_anchor, self._schedule.financial_weekday, self._schedule.financial_hour
            )),
            (HTWeekState.PRE_YOUTH_SCOUT, _event_datetime(
                sunday_anchor, self._schedule.youth_weekday, self._schedule.youth_hour
            )),
        ]
        upcoming = [(state, when) for state, when in candidates if when > now]
        if upcoming:
            return min(upcoming, key=lambda item: item[1])
        next_match = _event_datetime(
            sunday_anchor + timedelta(days=7), self._schedule.match_weekday, self._schedule.match_hour
        )
        return HTWeekState.POST_LEAGUE_MATCH, next_match

    def week_snapshot(self, now: datetime | None = None) -> HTWeekSnapshot:
        """Everything a caller needs about the current week in one
        call -- the shape most UI/service consumers actually want."""
        now = now or self.now()
        sunday_anchor = _most_recent_sunday(now.date())
        match_at = _event_datetime(sunday_anchor, self._schedule.match_weekday, self._schedule.match_hour)
        friendly_at = _event_datetime(
            sunday_anchor, self._schedule.friendly_weekday, self._schedule.friendly_hour
        )
        financial_at = _event_datetime(
            sunday_anchor, self._schedule.financial_weekday, self._schedule.financial_hour
        )
        youth_at = _event_datetime(sunday_anchor, self._schedule.youth_weekday, self._schedule.youth_hour)

        return HTWeekSnapshot(
            reference_time=now,
            weekday=self.current_weekday(now),
            state=self.current_state(now),
            training_week_id=self.training_week_id(now),
            training_processed=self.is_training_processed(now),
            league_match_played=now >= match_at,
            friendly_played=now >= friendly_at,
            financial_update_completed=now >= financial_at,
            youth_scout_completed=now >= youth_at,
            days_until_training=self.days_until_training(now),
            days_until_finances=self.days_until_finances(now),
            days_until_match=self.days_until_match(now),
        )

    # -- internals ---------------------------------------------------

    def _most_recent_training_boundary(self, now: datetime) -> datetime:
        target_weekday = self._schedule.training_weekday.python_weekday
        days_since = (now.weekday() - target_weekday) % 7
        candidate_date = now.date() - timedelta(days=days_since)
        candidate = datetime.combine(candidate_date, time(hour=self._schedule.training_hour))
        if candidate > now:
            candidate -= timedelta(days=7)
        return candidate

    def _days_until(self, weekday: HTWeekday, hour: int, now: datetime | None) -> int:
        """Whole calendar days until the next occurrence of this event
        (0 if it's later today)."""
        now = now or self.now()
        sunday_anchor = _most_recent_sunday(now.date())
        target = _event_datetime(sunday_anchor, weekday, hour)
        if target < now:
            target += timedelta(days=7)
        return max(0, (target.date() - now.date()).days)
