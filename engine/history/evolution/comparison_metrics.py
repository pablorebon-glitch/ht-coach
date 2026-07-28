from __future__ import annotations


def absolute_delta(previous: float | None, current: float | None) -> float | None:
    """current - previous, or None if either side is missing."""
    if previous is None or current is None:
        return None
    return current - previous


def percentage_delta(previous: float | None, current: float | None) -> float | None:
    """Percentage change of current relative to previous. None when
    either value is missing, or when previous is exactly zero (a
    percentage change from zero is undefined, not infinite)."""
    if previous is None or current is None:
        return None
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100.0


def safe_average(values) -> float | None:
    """Average of the non-None values in `values`. None if there are
    no comparable values at all."""
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return sum(usable) / len(usable)
