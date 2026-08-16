from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleEvaluationContext:
    """Everything a role/status rule may read: the player context, the
    squad-relative context, and the already-classified dimensions (so
    role rules never recompute a dimension themselves)."""

    player_context: object
    squad_context: object
    current_performance: object
    training_potential: object
    training_fit: object
    salary_efficiency: object
    strategic_value: object


class RoleRule:
    """One deterministic candidate-role rule. Returns zero or one
    (role, priority, evidence) candidates -- never asserts a role
    without evidence."""

    rule_id: str = ""
    priority: int = 0

    def evaluate(self, context: RoleEvaluationContext):
        raise NotImplementedError


class StatusRule:
    """One deterministic candidate-status rule, evaluated after a role
    has already been resolved (some status rules read the resolved
    role)."""

    rule_id: str = ""
    priority: int = 0

    def evaluate(self, context: RoleEvaluationContext, resolved_role):
        raise NotImplementedError
