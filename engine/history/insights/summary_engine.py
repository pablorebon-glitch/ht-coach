from __future__ import annotations

from engine.history.evolution.comparison_models import Trend
from engine.history.insights.enums import (
    InsightCategory,
    InsightConfidence,
    InsightDirection,
    InsightRelationship,
)
from engine.history.insights.models import ExecutiveSummary

_IMPROVED_TRENDS = (Trend.IMPROVEMENT, Trend.MAJOR_IMPROVEMENT)
_DECLINED_TRENDS = (Trend.DECLINE, Trend.MAJOR_DECLINE)

_CONFIDENCE_RANK = {
    InsightConfidence.HIGH: 3,
    InsightConfidence.MEDIUM: 2,
    InsightConfidence.LOW: 1,
    InsightConfidence.INSUFFICIENT_DATA: 0,
}

_CONTRIBUTOR_RELATIONSHIPS = (
    InsightRelationship.LIKELY_CONTRIBUTOR,
    InsightRelationship.POSSIBLE_CONTRIBUTOR,
)


def _rank(insight):
    return (_CONFIDENCE_RANK[insight.confidence], insight.priority)


def _overall_direction(evolution) -> InsightDirection:
    overall = evolution.overall
    if overall.improved_sector_count > 0 and overall.declined_sector_count > 0:
        return InsightDirection.MIXED
    if overall.overall_trend in _IMPROVED_TRENDS:
        return InsightDirection.POSITIVE
    if overall.overall_trend in _DECLINED_TRENDS:
        return InsightDirection.NEGATIVE
    return InsightDirection.NEUTRAL


def _best_matching(insights, predicate):
    candidates = [insight for insight in insights if predicate(insight)]
    if not candidates:
        return None
    return max(candidates, key=_rank)


def _missing_ratings_limitation(evolution) -> str:
    incomplete = any(
        sector.previous_value is None or sector.current_value is None
        for sector in evolution.sectors
    )
    return "insight.limitation.missing_ratings" if incomplete else ""


def build_executive_summary(
    evolution,
    insights,
    comparison_target_key: str = "",
) -> ExecutiveSummary:
    """Builds the structured executive summary from already-generated
    insights. Never generates free-form text — only picks among
    existing structured insights and returns keys/values."""
    overall_direction = _overall_direction(evolution)

    main_improvement = _best_matching(
        insights,
        lambda insight: (
            insight.category == InsightCategory.SECTOR_PERFORMANCE
            and insight.direction == InsightDirection.POSITIVE
        ),
    )
    main_decline = _best_matching(
        insights,
        lambda insight: (
            insight.category == InsightCategory.SECTOR_PERFORMANCE
            and insight.direction == InsightDirection.NEGATIVE
        ),
    )
    strongest_contributor = _best_matching(
        insights,
        lambda insight: insight.relationship in _CONTRIBUTOR_RELATIONSHIPS,
    )

    candidates_for_confidence = [
        candidate
        for candidate in (main_improvement, main_decline, strongest_contributor)
        if candidate is not None
    ]
    confidence = (
        max(candidates_for_confidence, key=_rank).confidence
        if candidates_for_confidence
        else InsightConfidence.INSUFFICIENT_DATA
    )

    return ExecutiveSummary(
        comparison_target_key=comparison_target_key,
        overall_direction=overall_direction,
        main_improvement=main_improvement,
        main_decline=main_decline,
        strongest_contributor=strongest_contributor,
        confidence=confidence,
        limitation_key=_missing_ratings_limitation(evolution),
    )
