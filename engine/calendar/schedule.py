from __future__ import annotations

from dataclasses import dataclass

from engine.calendar.enums import HTWeekday


@dataclass(frozen=True)
class HTWeekScheduleConfig:
    """Configurable server-local processing hour (0-23) for each weekly
    HT event -- the single place these are ever set. Defaults are HT
    Coach's best-effort approximation of a typical Hattrick server
    schedule; the only hour explicitly given in this sprint's brief is
    training (21:00). The others are reasonable estimates and are
    intentionally easy to override per-league if real usage shows a
    different schedule."""

    match_weekday: HTWeekday = HTWeekday.SUNDAY
    match_hour: int = 16

    friendly_weekday: HTWeekday = HTWeekday.WEDNESDAY
    friendly_hour: int = 20

    training_weekday: HTWeekday = HTWeekday.THURSDAY
    training_hour: int = 21

    financial_weekday: HTWeekday = HTWeekday.FRIDAY
    financial_hour: int = 8

    youth_weekday: HTWeekday = HTWeekday.SATURDAY
    youth_hour: int = 10


DEFAULT_SCHEDULE = HTWeekScheduleConfig()
