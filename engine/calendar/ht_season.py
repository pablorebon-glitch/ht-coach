"""Hattrick's competitive season numbering (Alpha 0.6.6, Part 9).

Preserves a distinction the brief is explicit about: a *training cycle*
(Sunday-Saturday, Thursday-21:00 processing cutoff -- `HTCalendarService`'s
own concept, see `service.py`) is NOT the same thing as Hattrick's own
*competitive season week* numbering (Monday-Sunday, numbered inside the
season). A Match Record needs both, independently -- never merged, never one
derived from the other.

HT Coach deliberately never *computes* `season_number`/`season_week` from a
date. Hattrick's season boundaries aren't reliable calendar arithmetic (they
drift with server-specific scheduling, cup weeks, and season-length
variation), so guessing would produce a confidently wrong number -- worse
than not showing one. These are always explicitly provided, either by the
user or from an external data source that actually states them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HTSeasonWeek:
    season_number: int | None = None
    season_week: int | None = None

    @property
    def is_known(self) -> bool:
        return self.season_number is not None and self.season_week is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "season_number": self.season_number,
            "season_week": self.season_week,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "HTSeasonWeek":
        if not data:
            return cls()
        return cls(
            season_number=data.get("season_number"),
            season_week=data.get("season_week"),
        )


UNKNOWN_SEASON_WEEK = HTSeasonWeek()
