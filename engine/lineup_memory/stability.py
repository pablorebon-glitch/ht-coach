"""Recommendation stability policy (Alpha 0.6.6, Part 3).

Never changes a saved lineup for a negligible optimization difference
without explaining it -- a pure recommendation/presentation policy applied
*after* optimization. Never modifies optimizer formulas; it only reads
already-computed deltas from a `MatchPlanRevision` and classifies how
meaningful the change actually is, combining several signals rather than one
arbitrary player score.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StabilityClassification(str, Enum):
    CLEAR_IMPROVEMENT = "clear_improvement"
    MODERATE_IMPROVEMENT = "moderate_improvement"
    MARGINAL_CHANGE = "marginal_change"
    EQUIVALENT = "equivalent"
    TRADE_OFF = "trade_off"


@dataclass(frozen=True)
class StabilityThresholds:
    clear_win_probability_delta: float = 0.05
    moderate_win_probability_delta: float = 0.02
    marginal_win_probability_delta: float = 0.005
    clear_xg_delta: float = 0.15
    moderate_xg_delta: float = 0.05
    marginal_xg_delta: float = 0.02
    trade_off_sector_delta: float = 0.10


DEFAULT_THRESHOLDS = StabilityThresholds()


def classify_stability(revision, thresholds: StabilityThresholds = DEFAULT_THRESHOLDS):
    if not revision.has_previous_plan or not revision.has_changes:
        return StabilityClassification.EQUIVALENT

    win_delta = revision.win_probability_delta
    xg_delta = revision.xg_delta

    gains = sum(1 for item in revision.sector_deltas if item.delta >= thresholds.trade_off_sector_delta)
    losses = sum(1 for item in revision.sector_deltas if item.delta <= -thresholds.trade_off_sector_delta)
    is_trade_off = gains > 0 and losses > 0

    strong_signal = (
        win_delta >= thresholds.clear_win_probability_delta
        or xg_delta >= thresholds.clear_xg_delta
    )
    moderate_signal = (
        win_delta >= thresholds.moderate_win_probability_delta
        or xg_delta >= thresholds.moderate_xg_delta
    )
    marginal_signal = (
        abs(win_delta) >= thresholds.marginal_win_probability_delta
        or abs(xg_delta) >= thresholds.marginal_xg_delta
    )

    if is_trade_off and not strong_signal:
        return StabilityClassification.TRADE_OFF
    if strong_signal:
        return StabilityClassification.CLEAR_IMPROVEMENT
    if moderate_signal:
        return StabilityClassification.MODERATE_IMPROVEMENT
    if marginal_signal:
        return StabilityClassification.MARGINAL_CHANGE
    return StabilityClassification.EQUIVALENT


def recommends_keeping_previous_lineup(classification) -> bool:
    return classification in (
        StabilityClassification.EQUIVALENT,
        StabilityClassification.MARGINAL_CHANGE,
    )
