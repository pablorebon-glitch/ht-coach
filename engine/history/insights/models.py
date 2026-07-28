from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.history.insights.enums import (
    InsightCategory,
    InsightConfidence,
    InsightDirection,
    InsightRelationship,
    InsightSeverity,
)
from engine.history.insights.evidence import InsightEvidence


@dataclass(frozen=True)
class HistoricalInsight:
    """A single structured, deterministic finding. Domain rules never
    return translated strings — `title_key`/`message_key` are stable
    localization keys and `message_params` are the structured values a
    UI/localization layer interpolates into them."""

    rule_id: str
    category: InsightCategory
    direction: InsightDirection
    relationship: InsightRelationship
    title_key: str
    message_key: str
    message_params: dict[str, Any] = field(default_factory=dict)
    evidence: tuple[InsightEvidence, ...] = ()
    affected_sectors: tuple[str, ...] = ()
    confidence: InsightConfidence = InsightConfidence.INSUFFICIENT_DATA
    severity: InsightSeverity = InsightSeverity.MINOR
    priority: int = 0
    limitations: tuple[str, ...] = ()
    dedupe_key: str = ""
    excludes: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.evidence and self.confidence != InsightConfidence.INSUFFICIENT_DATA:
            raise ValueError(
                f"insight '{self.rule_id}' has no evidence but claims "
                f"confidence={self.confidence.value}; evidence-less insights "
                "must be INSUFFICIENT_DATA"
            )
        if not self.dedupe_key:
            object.__setattr__(self, "dedupe_key", self.rule_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category.value,
            "direction": self.direction.value,
            "relationship": self.relationship.value,
            "title_key": self.title_key,
            "message_key": self.message_key,
            "message_params": dict(self.message_params),
            "evidence": [item.to_dict() for item in self.evidence],
            "affected_sectors": list(self.affected_sectors),
            "confidence": self.confidence.value,
            "severity": self.severity.value,
            "priority": self.priority,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class ExecutiveSummary:
    comparison_target_key: str = ""
    overall_direction: InsightDirection = InsightDirection.NEUTRAL
    main_improvement: HistoricalInsight | None = None
    main_decline: HistoricalInsight | None = None
    strongest_contributor: HistoricalInsight | None = None
    confidence: InsightConfidence = InsightConfidence.INSUFFICIENT_DATA
    limitation_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_target_key": self.comparison_target_key,
            "overall_direction": self.overall_direction.value,
            "main_improvement": (
                self.main_improvement.to_dict() if self.main_improvement else None
            ),
            "main_decline": (
                self.main_decline.to_dict() if self.main_decline else None
            ),
            "strongest_contributor": (
                self.strongest_contributor.to_dict()
                if self.strongest_contributor
                else None
            ),
            "confidence": self.confidence.value,
            "limitation_key": self.limitation_key,
        }


@dataclass(frozen=True)
class InsightResult:
    current_snapshot_id: str
    previous_snapshot_id: str
    insights: tuple[HistoricalInsight, ...]
    summary: ExecutiveSummary
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_snapshot_id": self.current_snapshot_id,
            "previous_snapshot_id": self.previous_snapshot_id,
            "insights": [insight.to_dict() for insight in self.insights],
            "summary": self.summary.to_dict(),
            "limitations": list(self.limitations),
        }
