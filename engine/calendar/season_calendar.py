"""HT Season Calendar configuration and resolution (Alpha 0.6.7 HF-02,
Parts 11-12).

HT Coach still never *guesses* a season/week -- see `engine/calendar/
ht_season.py`'s own docstring. What changes here: once the user has
explicitly told HT Coach an anchor point ("season 95 starts 2026-07-27"),
deriving week numbers *from that known anchor* is deterministic arithmetic,
not guessing. Without a configured anchor, resolution always returns
"unknown" -- never a fabricated number.

The competitive week (Monday-Sunday) is a completely separate concept from
the training cycle (Sunday-Saturday, `engine/calendar/service.py`). Never
merged.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from engine.calendar.ht_season import HTSeasonWeek

DEFAULT_TOTAL_WEEKS = 16


@dataclass(frozen=True)
class SeasonCalendarConfig:
    season_number: int | None = None
    season_start_date: str = ""
    total_weeks: int = DEFAULT_TOTAL_WEEKS
    timezone: str = "America/Buenos_Aires"

    @property
    def is_configured(self) -> bool:
        return self.season_number is not None and bool(self.season_start_date)

    @property
    def start_date_value(self):
        if not self.season_start_date:
            return None
        try:
            return date.fromisoformat(self.season_start_date[:10])
        except ValueError:
            return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "season_number": self.season_number,
            "season_start_date": self.season_start_date,
            "total_weeks": self.total_weeks,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(
            season_number=data.get("season_number"),
            season_start_date=data.get("season_start_date", ""),
            total_weeks=int(data.get("total_weeks", DEFAULT_TOTAL_WEEKS)),
            timezone=data.get("timezone", "America/Buenos_Aires"),
        )


@dataclass(frozen=True)
class SeasonContextResult:
    season_week: HTSeasonWeek = HTSeasonWeek()
    season_start_date: str = ""
    confidence: str = "unknown"
    provenance: str = ""

    @property
    def is_known(self) -> bool:
        return self.season_week.is_known


def _monday_on_or_before(value):
    return value - timedelta(days=value.weekday())


def resolve_season_context(match_date, config):
    if not config.is_configured:
        return SeasonContextResult(confidence="unconfigured", provenance="no_season_configured")

    if isinstance(match_date, str):
        try:
            match_date = date.fromisoformat(match_date[:10])
        except ValueError:
            return SeasonContextResult(confidence="unknown", provenance="invalid_match_date")
    if not isinstance(match_date, date):
        return SeasonContextResult(confidence="unknown", provenance="invalid_match_date")

    configured_start = config.start_date_value
    if configured_start is None:
        return SeasonContextResult(confidence="unconfigured", provenance="invalid_season_start_date")
    configured_start = _monday_on_or_before(configured_start)

    total_weeks = max(1, config.total_weeks)
    season_span = timedelta(weeks=total_weeks)
    configured_end = configured_start + season_span - timedelta(days=1)

    if configured_start <= match_date <= configured_end:
        week_index = (match_date - configured_start).days // 7
        return SeasonContextResult(
            season_week=HTSeasonWeek(
                season_number=config.season_number,
                season_week=week_index + 1,
            ),
            season_start_date=configured_start.isoformat(),
            confidence="configured",
            provenance="within_configured_season",
        )

    if match_date < configured_start:
        previous_start = configured_start - season_span
        previous_end = configured_start - timedelta(days=1)
        if previous_start <= match_date <= previous_end and config.season_number is not None:
            week_index = (match_date - previous_start).days // 7
            return SeasonContextResult(
                season_week=HTSeasonWeek(
                    season_number=config.season_number - 1,
                    season_week=week_index + 1,
                ),
                season_start_date=previous_start.isoformat(),
                confidence="inferred_adjacent",
                provenance="one_season_before_configured",
            )
        return SeasonContextResult(confidence="unknown", provenance="too_far_before_configured_season")

    next_start = configured_end + timedelta(days=1)
    next_end = next_start + season_span - timedelta(days=1)
    if next_start <= match_date <= next_end and config.season_number is not None:
        week_index = (match_date - next_start).days // 7
        return SeasonContextResult(
            season_week=HTSeasonWeek(
                season_number=config.season_number + 1,
                season_week=week_index + 1,
            ),
            season_start_date=next_start.isoformat(),
            confidence="inferred_adjacent",
            provenance="one_season_after_configured",
        )
    return SeasonContextResult(confidence="unknown", provenance="too_far_after_configured_season")
