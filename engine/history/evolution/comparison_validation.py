from __future__ import annotations


class EvolutionComparisonError(ValueError):
    pass


def ensure_comparable(current, previous) -> None:
    """Raises EvolutionComparisonError if the two snapshots can't be
    meaningfully compared at all. This is intentionally narrow: missing
    *optional* data (ratings, tactic, lineup, predictions) is handled
    gracefully field-by-field inside the comparison engine and is NOT
    an error here — only structurally missing snapshots are."""
    if current is None:
        raise EvolutionComparisonError("current snapshot is required")
    if previous is None:
        raise EvolutionComparisonError("previous snapshot is required")
    if current.snapshot_id == previous.snapshot_id:
        raise EvolutionComparisonError(
            "current and previous snapshots must be different"
        )
