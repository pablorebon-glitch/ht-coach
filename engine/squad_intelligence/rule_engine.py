from __future__ import annotations

from engine.squad_intelligence.roles import default_role_rules
from engine.squad_intelligence.statuses import default_status_rules


class SquadIntelligenceRuleEngine:
    """Evaluates every role rule, keeps the highest-priority match (the
    guaranteed DepthPlayerRule fallback ensures there's always at least
    one), then does the same for status rules given the resolved role.
    Deterministic: ties break on rule_id for reproducibility."""

    def __init__(self, role_rules=None, status_rules=None):
        self.role_rules = tuple(role_rules) if role_rules is not None else default_role_rules()
        self.status_rules = (
            tuple(status_rules) if status_rules is not None else default_status_rules()
        )

    def resolve_role(self, context):
        candidates = []
        for rule in self.role_rules:
            result = rule.evaluate(context)
            if result is not None:
                role, priority, evidence = result
                candidates.append((priority, rule.rule_id, role, evidence))
        if not candidates:
            raise RuntimeError(
                "no role rule matched -- DepthPlayerRule should always match; "
                "check that it's included in the rule set"
            )
        candidates.sort(key=lambda item: (-item[0], item[1]))
        _, _, role, evidence = candidates[0]
        return role, evidence

    def resolve_status(self, context, resolved_role):
        candidates = []
        for rule in self.status_rules:
            result = rule.evaluate(context, resolved_role)
            if result is not None:
                status, priority, evidence = result
                candidates.append((priority, rule.rule_id, status, evidence))
        if not candidates:
            raise RuntimeError(
                "no status rule matched -- MonitorStatusRule should always "
                "match; check that it's included in the rule set"
            )
        candidates.sort(key=lambda item: (-item[0], item[1]))
        _, _, status, evidence = candidates[0]
        return status, evidence
