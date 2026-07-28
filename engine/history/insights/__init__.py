from __future__ import annotations

from engine.history.insights.models import InsightResult
from engine.history.insights.rule import InsightContext
from engine.history.insights.rule_engine import InsightRuleEngine, default_rule_catalog
from engine.history.insights.summary_engine import build_executive_summary
from engine.history.insights.validation import (
    InsightGenerationError,
    ensure_insight_context_valid,
)

_ENGINE = InsightRuleEngine()


def generate_insights(
    current_snapshot,
    previous_snapshot,
    evolution_result,
    comparison_target_key: str = "",
    engine: InsightRuleEngine | None = None,
) -> InsightResult:
    """Turns a HistoricalEvolutionResult into deterministic, evidenced
    insights plus an executive summary. Pure function of its inputs —
    no I/O, no Qt, no AI."""
    context = InsightContext(
        current_snapshot=current_snapshot,
        previous_snapshot=previous_snapshot,
        evolution=evolution_result,
    )
    engine = engine or _ENGINE
    insights = engine.evaluate(context)
    summary = build_executive_summary(evolution_result, insights, comparison_target_key)
    limitations = tuple(
        sorted({limitation for insight in insights for limitation in insight.limitations})
    )
    return InsightResult(
        current_snapshot_id=current_snapshot.snapshot_id,
        previous_snapshot_id=previous_snapshot.snapshot_id,
        insights=insights,
        summary=summary,
        limitations=limitations,
    )


__all__ = [
    "generate_insights",
    "InsightRuleEngine",
    "default_rule_catalog",
    "InsightContext",
    "InsightResult",
    "InsightGenerationError",
    "ensure_insight_context_valid",
]
