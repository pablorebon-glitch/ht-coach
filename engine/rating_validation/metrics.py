from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


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
    )
