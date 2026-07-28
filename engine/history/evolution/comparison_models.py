from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.history.enums import _StableEnum


class Trend(_StableEnum):
    MAJOR_IMPROVEMENT = "major_improvement"
    IMPROVEMENT = "improvement"
    UNCHANGED = "unchanged"
    DECLINE = "decline"
    MAJOR_DECLINE = "major_decline"


@dataclass(frozen=True)
class TrendThresholds:
    """Configurable thresholds used to classify a percentage delta into
    a Trend. Never hardcode these inside comparison logic; pass an
    instance through instead (a default is provided for convenience).

    `unchanged_band` is the +/- percentage-point band around zero that
    counts as UNCHANGED. `major_band` is the percentage-point magnitude
    beyond which a change is classified as "major" rather than a plain
    improvement/decline.
    """

    unchanged_band: float = 1.0
    major_band: float = 10.0

    def __post_init__(self):
        if self.unchanged_band < 0:
            raise ValueError("unchanged_band must be >= 0")
        if self.major_band < self.unchanged_band:
            raise ValueError("major_band must be >= unchanged_band")

    def to_dict(self) -> dict[str, Any]:
        return {
            "unchanged_band": self.unchanged_band,
            "major_band": self.major_band,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TrendThresholds":
        data = data or {}
        return cls(
            unchanged_band=float(data.get("unchanged_band", 1.0)),
            major_band=float(data.get("major_band", 10.0)),
        )


DEFAULT_TREND_THRESHOLDS = TrendThresholds()


def classify_trend(
    percentage_delta: float | None,
    thresholds: TrendThresholds | None = None,
) -> Trend:
    """Classifies a percentage delta (current vs. previous, e.g. +12.5
    for a 12.5% improvement) into a Trend, using the given (or default)
    thresholds. A None delta (nothing comparable) is UNCHANGED."""
    thresholds = thresholds or DEFAULT_TREND_THRESHOLDS
    if percentage_delta is None:
        return Trend.UNCHANGED
    if abs(percentage_delta) <= thresholds.unchanged_band:
        return Trend.UNCHANGED
    if percentage_delta > 0:
        return (
            Trend.MAJOR_IMPROVEMENT
            if percentage_delta >= thresholds.major_band
            else Trend.IMPROVEMENT
        )
    return (
        Trend.MAJOR_DECLINE
        if percentage_delta <= -thresholds.major_band
        else Trend.DECLINE
    )


@dataclass(frozen=True)
class SectorEvolution:
    sector: str
    previous_value: float | None
    current_value: float | None
    absolute_delta: float | None
    percentage_delta: float | None
    trend: Trend

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector": self.sector,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "absolute_delta": self.absolute_delta,
            "percentage_delta": self.percentage_delta,
            "trend": self.trend.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectorEvolution":
        return cls(
            sector=data["sector"],
            previous_value=data.get("previous_value"),
            current_value=data.get("current_value"),
            absolute_delta=data.get("absolute_delta"),
            percentage_delta=data.get("percentage_delta"),
            trend=Trend.parse(data.get("trend", Trend.UNCHANGED.value)),
        )
