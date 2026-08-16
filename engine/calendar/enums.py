"""The canonical Hattrick weekly cycle -- typed enums only. No datetime
arithmetic lives here; see `service.py` for that.
"""
from __future__ import annotations

from enum import Enum


class _StableEnum(str, Enum):
    """Same stability contract used throughout HT Coach's domain
    layers: `.value` is a permanent, storage-safe string -- never
    renamed once shipped."""

    @classmethod
    def parse(cls, value):
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError as exc:
            raise ValueError(f"invalid {cls.__name__}: {value}") from exc


class HTWeekday(_StableEnum):
    """Hattrick's own weekly rhythm -- deliberately not `datetime`'s
    Monday-first weekday numbering, since HT's week conceptually starts
    the day after the league match (Monday = recovery) and ends with
    the match itself (Sunday). Each day has exactly one canonical HT
    activity; see docs/HT_WEEK_CALENDAR.md for why this differs from a
    real-world calendar week."""

    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"

    @property
    def python_weekday(self) -> int:
        """Python's `date.weekday()` convention (Monday=0..Sunday=6),
        for the one place this module needs to talk to `datetime`."""
        return _PYTHON_WEEKDAY[self]


_PYTHON_WEEKDAY = {
    HTWeekday.MONDAY: 0,
    HTWeekday.TUESDAY: 1,
    HTWeekday.WEDNESDAY: 2,
    HTWeekday.THURSDAY: 3,
    HTWeekday.FRIDAY: 4,
    HTWeekday.SATURDAY: 5,
    HTWeekday.SUNDAY: 6,
}
_WEEKDAY_FROM_PYTHON = {value: key for key, value in _PYTHON_WEEKDAY.items()}

HT_DAY_ACTIVITY = {
    HTWeekday.SUNDAY: "league_or_cup_match",
    HTWeekday.MONDAY: "recovery",
    HTWeekday.TUESDAY: "preparation",
    HTWeekday.WEDNESDAY: "friendly",
    HTWeekday.THURSDAY: "training_update",
    HTWeekday.FRIDAY: "financial_update",
    HTWeekday.SATURDAY: "youth_scout",
}


class HTWeekState(_StableEnum):
    """The most recent major weekly milestone that has occurred,
    relative to `now` -- not a strict one-per-day state machine
    (several of these can be simultaneously true in reality;
    `current_state()` returns whichever milestone most recently
    passed). Every state answers "has this week's X already happened,
    or not yet?" for exactly one X at a time, matching what the
    brief's examples ask for."""

    PRE_LEAGUE_MATCH = "pre_league_match"
    POST_LEAGUE_MATCH = "post_league_match"
    PRE_FRIENDLY = "pre_friendly"
    POST_FRIENDLY = "post_friendly"
    PRE_TRAINING = "pre_training"
    POST_TRAINING = "post_training"
    POST_FINANCIAL_UPDATE = "post_financial_update"
    PRE_YOUTH_SCOUT = "pre_youth_scout"
