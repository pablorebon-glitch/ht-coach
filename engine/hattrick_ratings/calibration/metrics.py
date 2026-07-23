from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from statistics import median


@dataclass(frozen=True)
class CalibrationMetrics:
    sample_count: int = 0
    exact_accuracy: float = 0.0
    within_0_25_accuracy: float = 0.0
    within_0_50_accuracy: float = 0.0
    mean_absolute_error: Decimal = Decimal("0")
    median_absolute_error: Decimal = Decimal("0")
    signed_bias: Decimal = Decimal("0")
    maximum_error: Decimal = Decimal("0")
    minimum_error: Decimal = Decimal("0")
    confidence_distribution: dict[str, int] = field(default_factory=dict)
    warning_distribution: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SegmentMetrics:
    segment: str
    metrics: CalibrationMetrics


@dataclass(frozen=True)
class CalibrationReport:
    model_version: str
    dataset_size: int
    aggregate_metrics: CalibrationMetrics
    segments: dict[str, tuple[SegmentMetrics, ...]]
    excluded_records: tuple[str, ...] = ()
    recommendation: str = "insufficient_data"


def calculate_observation_metrics(observations) -> CalibrationMetrics:
    observations = tuple(observations)
    if not observations:
        return CalibrationMetrics()
    abs_errors = [item.absolute_error for item in observations]
    signed_errors = [item.signed_error for item in observations]
    count = len(observations)
    return CalibrationMetrics(
        sample_count=count,
        exact_accuracy=sum(1 for item in observations if item.exact_match) / count,
        within_0_25_accuracy=sum(1 for item in observations if item.within_0_25) / count,
        within_0_50_accuracy=sum(1 for item in observations if item.within_0_50) / count,
        mean_absolute_error=sum(abs_errors, Decimal("0")) / Decimal(count),
        median_absolute_error=median(abs_errors),
        signed_bias=sum(signed_errors, Decimal("0")) / Decimal(count),
        maximum_error=max(abs_errors),
        minimum_error=min(signed_errors),
        confidence_distribution=dict(Counter(item.confidence.value for item in observations)),
        warning_distribution=dict(Counter(warning for item in observations for warning in item.warnings)),
    )


def build_report(records, model_version: str) -> CalibrationReport:
    records = tuple(records)
    observations = [
        record.observations_by_model_version[model_version]
        for record in records
        if model_version in record.observations_by_model_version
    ]
    excluded = tuple(
        record.record_id
        for record in records
        if model_version not in record.observations_by_model_version
    )
    return CalibrationReport(
        model_version=model_version,
        dataset_size=len(records),
        aggregate_metrics=calculate_observation_metrics(observations),
        segments=_segments(records, model_version),
        excluded_records=excluded,
        recommendation=(
            "ready_for_manual_review"
            if len(observations) >= 30
            else "insufficient_data"
        ),
    )


def _segments(records, model_version):
    groups = {
        "formation": defaultdict(list),
        "home_or_away": defaultdict(list),
        "attitude": defaultdict(list),
        "team_spirit_available": defaultdict(list),
        "confidence": defaultdict(list),
        "unsupported_orders": defaultdict(list),
    }
    for record in records:
        observation = record.observations_by_model_version.get(model_version)
        if observation is None:
            continue
        groups["formation"][record.formation].append(observation)
        groups["home_or_away"][record.match_context.home_or_away or "unknown"].append(observation)
        groups["attitude"][record.match_context.team_attitude or "unknown"].append(observation)
        groups["team_spirit_available"][
            "known" if record.match_context.team_spirit is not None else "unknown"
        ].append(observation)
        groups["confidence"][observation.confidence.value].append(observation)
        groups["unsupported_orders"][
            "yes" if "unsupported_order" in observation.warnings else "no"
        ].append(observation)
    return {
        key: tuple(
            SegmentMetrics(segment=segment, metrics=calculate_observation_metrics(items))
            for segment, items in sorted(value.items())
        )
        for key, value in groups.items()
    }
