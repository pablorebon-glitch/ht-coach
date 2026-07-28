from __future__ import annotations

from engine.history.insights.enums import InsightSeverity

_HIGH_PRIORITY_SEVERITIES = (InsightSeverity.CRITICAL, InsightSeverity.NOTABLE)


def high_priority_insights(insights):
    return tuple(i for i in insights if i.severity in _HIGH_PRIORITY_SEVERITIES)


def other_insights(insights):
    return tuple(i for i in insights if i.severity not in _HIGH_PRIORITY_SEVERITIES)


def visual_hierarchy(result):
    """Orders a generated InsightResult into the four-tier visual
    hierarchy requested for the Insights Panel: executive summary,
    high-priority insights, other insights, limitations. Returns a
    dict of the four buckets rather than a single flattened list, so a
    future UI can render each with its own heading."""
    return {
        "summary": result.summary,
        "high_priority": high_priority_insights(result.insights),
        "other": other_insights(result.insights),
        "limitations": result.limitations,
    }


def format_evidence_summary(insight):
    """One row per evidence item: (entity_label_or_id, previous, current, delta)."""
    return [
        (
            item.entity_label or item.entity_id,
            item.previous_value,
            item.current_value,
            item.delta,
        )
        for item in insight.evidence
    ]
