from __future__ import annotations

from engine.history.insights.enums import InsightConfidence
from engine.history.insights.formation_rules import default_formation_rules
from engine.history.insights.lineup_rules import default_lineup_rules
from engine.history.insights.order_rules import default_order_rules
from engine.history.insights.player_condition_rules import (
    default_player_condition_rules,
)
from engine.history.insights.prediction_rules import default_prediction_rules
from engine.history.insights.sector_rules import default_sector_rules
from engine.history.insights.tactical_rules import default_tactical_rules
from engine.history.insights.validation import ensure_insight_context_valid

_CONFIDENCE_RANK = {
    InsightConfidence.HIGH: 3,
    InsightConfidence.MEDIUM: 2,
    InsightConfidence.LOW: 1,
    InsightConfidence.INSUFFICIENT_DATA: 0,
}


def default_rule_catalog() -> tuple:
    return (
        default_sector_rules()
        + default_formation_rules()
        + default_lineup_rules()
        + default_order_rules()
        + default_player_condition_rules()
        + default_tactical_rules()
        + default_prediction_rules()
    )


class InsightRuleEngine:
    """Evaluates every rule against a context, then deterministically
    deduplicates and prioritizes the results: for a given dedupe key
    (category + direction + affected sectors, by default), only the
    highest-priority insight survives, breaking ties by confidence.
    Rules that declare `excludes` are resolved the same way."""

    def __init__(self, rules=None):
        self.rules = tuple(rules) if rules is not None else default_rule_catalog()

    def evaluate(self, context) -> tuple:
        ensure_insight_context_valid(context)
        raw = []
        for rule in self.rules:
            raw.extend(rule.evaluate(context))
        deduplicated = self._deduplicate(raw)
        return tuple(
            sorted(deduplicated, key=lambda insight: (-insight.priority, insight.rule_id))
        )

    def _deduplicate(self, insights):
        best_by_key = {}
        for insight in insights:
            current_best = best_by_key.get(insight.dedupe_key)
            if current_best is None or self._is_better(insight, current_best):
                best_by_key[insight.dedupe_key] = insight
        return self._apply_exclusions(list(best_by_key.values()))

    @classmethod
    def _is_better(cls, candidate, current):
        if candidate.priority != current.priority:
            return candidate.priority > current.priority
        return (
            _CONFIDENCE_RANK[candidate.confidence]
            > _CONFIDENCE_RANK[current.confidence]
        )

    @staticmethod
    def _apply_exclusions(insights):
        by_id = {insight.rule_id: insight for insight in insights}
        excluded_ids = set()
        for insight in insights:
            for excluded_id in insight.excludes:
                other = by_id.get(excluded_id)
                if other is None:
                    continue
                loser = (
                    excluded_id
                    if insight.priority >= other.priority
                    else insight.rule_id
                )
                excluded_ids.add(loser)
        return [
            insight for insight in insights if insight.rule_id not in excluded_ids
        ]
