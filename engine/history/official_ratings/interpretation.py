"""Deterministic interpretation of the PRE-vs-POST official ratings
comparison (HF-02.2, Part 5/6). Keeps the exact values from
`compare_official_ratings` untouched -- this module only classifies
and summarizes them. Never claims a cause (stamina, weather,
substitutions) unless that evidence is actually available, which it
isn't yet anywhere in this pipeline -- conclusions here are always
phrased as an observation about the numbers, never a diagnosis of why.
"""
from __future__ import annotations

from dataclasses import dataclass

DIRECTION_IMPROVED = "improved"
DIRECTION_STABLE = "stable"
DIRECTION_DECLINED = "declined"

MAGNITUDE_STABLE = "stable"
MAGNITUDE_SMALL = "small"
MAGNITUDE_MODERATE = "moderate"
MAGNITUDE_LARGE = "large"

DEFENSE_SECTORS = ("left_defense", "central_defense", "right_defense")
ATTACK_SECTORS = ("left_attack", "central_attack", "right_attack")
MIDFIELD_SECTOR = "midfield"


@dataclass(frozen=True)
class InterpretationThresholds:
    stable_threshold: float = 0.25
    small_threshold: float = 0.50
    moderate_threshold: float = 1.00


DEFAULT_THRESHOLDS = InterpretationThresholds()


@dataclass(frozen=True)
class InterpretedSector:
    sector: str
    pre_value: float | None
    post_value: float | None
    delta: float | None
    direction: str | None
    magnitude: str | None


def classify_change(delta, thresholds: InterpretationThresholds = DEFAULT_THRESHOLDS):
    if delta is None:
        return None, None
    magnitude_value = abs(delta)
    if magnitude_value < thresholds.stable_threshold:
        return DIRECTION_STABLE, MAGNITUDE_STABLE
    direction = DIRECTION_IMPROVED if delta > 0 else DIRECTION_DECLINED
    if magnitude_value < thresholds.small_threshold:
        magnitude = MAGNITUDE_SMALL
    elif magnitude_value < thresholds.moderate_threshold:
        magnitude = MAGNITUDE_MODERATE
    else:
        magnitude = MAGNITUDE_LARGE
    return direction, magnitude


def interpret_comparison(comparison, thresholds: InterpretationThresholds = DEFAULT_THRESHOLDS):
    interpreted = []
    for sector in comparison.sectors:
        direction, magnitude = classify_change(sector.pre_vs_post_delta, thresholds)
        interpreted.append(
            InterpretedSector(
                sector=sector.sector,
                pre_value=sector.official_pre_value,
                post_value=sector.official_post_value,
                delta=sector.pre_vs_post_delta,
                direction=direction,
                magnitude=magnitude,
            )
        )
    return tuple(interpreted)


@dataclass(frozen=True)
class Conclusion:
    key: str
    params: dict


def generate_conclusions(interpreted_sectors):
    conclusions = []

    known = [item for item in interpreted_sectors if item.delta is not None]
    unknown_sectors = [item.sector for item in interpreted_sectors if item.delta is None]

    if not known:
        conclusions.append(Conclusion("official_match_intelligence.conclusion.no_data", {}))
        return tuple(conclusions)

    improvements = [item for item in known if item.direction == DIRECTION_IMPROVED]
    declines = [item for item in known if item.direction == DIRECTION_DECLINED]

    if improvements:
        best = max(improvements, key=lambda item: item.delta)
        conclusions.append(
            Conclusion(
                "official_match_intelligence.conclusion.largest_improvement",
                {"sector": best.sector, "delta": best.delta},
            )
        )
    if declines:
        worst = min(declines, key=lambda item: item.delta)
        conclusions.append(
            Conclusion(
                "official_match_intelligence.conclusion.largest_decline",
                {"sector": worst.sector, "delta": worst.delta},
            )
        )

    stable = [item.sector for item in known if item.direction == DIRECTION_STABLE]
    if stable:
        conclusions.append(
            Conclusion(
                "official_match_intelligence.conclusion.stable_sectors",
                {"count": len(stable), "sectors": ", ".join(stable)},
            )
        )

    if improvements or declines:
        conclusions.append(
            Conclusion(
                "official_match_intelligence.conclusion.overall_split",
                {"improved": len(improvements), "declined": len(declines)},
            )
        )

    defensive_trend = _group_trend(known, DEFENSE_SECTORS)
    if defensive_trend is not None:
        conclusions.append(
            Conclusion(
                f"official_match_intelligence.conclusion.defensive_trend.{defensive_trend}",
                {},
            )
        )
    attacking_trend = _group_trend(known, ATTACK_SECTORS)
    if attacking_trend is not None:
        conclusions.append(
            Conclusion(
                f"official_match_intelligence.conclusion.attacking_trend.{attacking_trend}",
                {},
            )
        )
    midfield_item = next((item for item in known if item.sector == MIDFIELD_SECTOR), None)
    if midfield_item is not None:
        conclusions.append(
            Conclusion(
                f"official_match_intelligence.conclusion.midfield_trend.{midfield_item.direction}",
                {},
            )
        )

    if unknown_sectors:
        conclusions.append(
            Conclusion(
                "official_match_intelligence.conclusion.missing_data",
                {"count": len(unknown_sectors)},
            )
        )

    return tuple(conclusions)


def _group_trend(known_items, group_sectors):
    group_items = [item for item in known_items if item.sector in group_sectors]
    if not group_items:
        return None
    improved = sum(1 for item in group_items if item.direction == DIRECTION_IMPROVED)
    declined = sum(1 for item in group_items if item.direction == DIRECTION_DECLINED)
    if improved > declined:
        return DIRECTION_IMPROVED
    if declined > improved:
        return DIRECTION_DECLINED
    return DIRECTION_STABLE
