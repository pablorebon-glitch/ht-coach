from __future__ import annotations


class InsightGenerationError(ValueError):
    pass


def ensure_insight_context_valid(context) -> None:
    if context.current_snapshot is None:
        raise InsightGenerationError("current snapshot is required")
    if context.previous_snapshot is None:
        raise InsightGenerationError("previous snapshot is required")
    if context.evolution is None:
        raise InsightGenerationError("evolution result is required")
    if (
        context.evolution.current_snapshot_id != context.current_snapshot.snapshot_id
        or context.evolution.previous_snapshot_id
        != context.previous_snapshot.snapshot_id
    ):
        raise InsightGenerationError(
            "evolution result does not match the given snapshots"
        )
