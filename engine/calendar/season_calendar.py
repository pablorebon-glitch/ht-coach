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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from engine.calendar.ht_season import HTSeasonWeek

DEFAULT_TOTAL_WEEKS = 16
SEASON_CALENDAR_SCHEMA_VERSION = 1
DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"
TIMEZONE_ALIASES = {
    "America/Buenos_Aires": DEFAULT_TIMEZONE,
}


@dataclass(frozen=True)
class SeasonCalendarConfig:
    season_number: int | None = None
    season_start_date: str = ""
    total_weeks: int = DEFAULT_TOTAL_WEEKS
    timezone: str = DEFAULT_TIMEZONE
    updated_at: str = ""
    schema_version: int = SEASON_CALENDAR_SCHEMA_VERSION

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

    @property
    def current_season_number(self):
        return self.season_number

    @property
    def current_season_start_date(self):
        return self.season_start_date

    @property
    def competitive_weeks(self):
        return self.total_weeks

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "current_season_number": self.season_number,
            "current_season_start_date": self.season_start_date,
            "competitive_weeks": self.total_weeks,
            "season_number": self.season_number,
            "season_start_date": self.season_start_date,
            "total_weeks": self.total_weeks,
            "timezone": self.timezone,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        season_number = data.get("current_season_number", data.get("season_number"))
        start_date = data.get(
            "current_season_start_date", data.get("season_start_date", "")
        )
        total_weeks = data.get("competitive_weeks", data.get("total_weeks", DEFAULT_TOTAL_WEEKS))
        return cls(
            season_number=season_number,
            season_start_date=start_date,
            total_weeks=int(total_weeks),
            timezone=data.get("timezone", DEFAULT_TIMEZONE),
            updated_at=data.get("updated_at", ""),
            schema_version=int(data.get("schema_version", SEASON_CALENDAR_SCHEMA_VERSION)),
        )


def validate_season_calendar_config(config):
    errors = []
    warnings = []
    if config.season_number is None or int(config.season_number) <= 0:
        errors.append("season_number_must_be_positive")
    if int(config.total_weeks or 0) <= 0:
        errors.append("competitive_weeks_must_be_positive")
    start = config.start_date_value
    if start is None:
        errors.append("season_start_date_invalid")
    elif start.weekday() != 0:
        warnings.append("season_start_date_not_monday")
    try:
        ZoneInfo(TIMEZONE_ALIASES.get(config.timezone, config.timezone))
    except ZoneInfoNotFoundError:
        errors.append("timezone_invalid")
    return tuple(errors), tuple(warnings)


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
