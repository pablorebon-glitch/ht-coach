from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import median


@dataclass(frozen=True)
class ErrorMetrics:
    count: int = 0
    ignored_count: int = 0
    comparison_count: int = 0
    absolute_error: float = 0.0
    mean_absolute_error: float = 0.0
    maximum_error: float = 0.0
    root_mean_squared_error: float = 0.0
    mean_signed_error: float = 0.0
    median_absolute_error: float = 0.0
    exact_quarter_accuracy: float = 0.0
    within_025_accuracy: float = 0.0
    within_050_accuracy: float = 0.0


def calculate_error_metrics(errors: list[float], ignored_count: int = 0) -> ErrorMetrics:
    if not errors:
        return ErrorMetrics(ignored_count=ignored_count)

    absolute_errors = [abs(error) for error in errors]
    count = len(errors)
    absolute_error = sum(absolute_errors)
    return ErrorMetrics(
        count=count,
        ignored_count=ignored_count,
        comparison_count=count,
        absolute_error=absolute_error,
        mean_absolute_error=absolute_error / count,
        maximum_error=max(absolute_errors),
        root_mean_squared_error=sqrt(sum(error * error for error in errors) / count),
        mean_signed_error=sum(errors) / count,
        median_absolute_error=median(absolute_errors),
        exact_quarter_accuracy=_within(absolute_errors, 0.0),
        within_025_accuracy=_within(absolute_errors, 0.25),
        within_050_accuracy=_within(absolute_errors, 0.50),
    )


def _within(absolute_errors: list[float], threshold: float) -> float:
    if not absolute_errors:
        return 0.0
    return sum(1 for error in absolute_errors if error <= threshold) / len(
        absolute_errors
    )
