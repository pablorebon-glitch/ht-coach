from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InsightContext:
    """Everything a rule may read. Rules must not reach outside this
    context (no re-fetching snapshots, no calling optimizers, no I/O)."""

    current_snapshot: object
    previous_snapshot: object
    evolution: object  # HistoricalEvolutionResult


class InsightRule:
    """Base class for a single deterministic rule. Subclasses implement
    `evaluate()` and return zero or more insights — most rules return
    zero or one, but a rule covering several similar entities (e.g.
    "player form changed") may return one insight per entity or a single
    aggregated one; that choice is the rule's responsibility."""

    rule_id: str = ""
    category = None
    priority: int = 0

    def evaluate(self, context: InsightContext) -> tuple:
        raise NotImplementedError
