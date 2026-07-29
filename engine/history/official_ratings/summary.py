from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OfficialRatingSummary:
    """Diagnostic prediction-accuracy information — explicitly *not*
    meant to be the primary Match UI (per this sprint's brief), but
    useful for a future Advisor/Decision Validation sprint and for
    anyone inspecting how good HT Coach's own predictions are."""

    compared_against: str = ""  # "official_pre" | "official_post"
    average_error: float | None = None
    maximum_error: float | None = None
    closest_sector: str | None = None
    closest_sector_error: float | None = None
    furthest_sector: str | None = None
    furthest_sector_error: float | None = None
    missing_sectors: tuple[str, ...] = ()
    confidence: str = "insufficient_data"  # "high" | "medium" | "low" | "insufficient_data"

    def to_dict(self) -> dict[str, Any]:
        return {
            "compared_against": self.compared_against,
            "average_error": self.average_error,
            "maximum_error": self.maximum_error,
            "closest_sector": self.closest_sector,
            "closest_sector_error": self.closest_sector_error,
            "furthest_sector": self.furthest_sector,
            "furthest_sector_error": self.furthest_sector_error,
            "missing_sectors": list(self.missing_sectors),
            "confidence": self.confidence,
        }


def _confidence_for(sample_count, total_count):
    if sample_count == 0:
        return "insufficient_data"
    coverage_ratio = sample_count / total_count
    if coverage_ratio >= 0.85:
        return "high"
    if coverage_ratio >= 0.5:
        return "medium"
    return "low"


def summarize_official_rating_comparison(comparison, compared_against="official_pre"):
    """Builds a diagnostic summary from an `OfficialRatingComparison`.
    `compared_against` selects which delta field to summarize —
    "official_pre" uses `predicted_vs_pre_delta`, "official_post" uses
    `predicted_vs_post_delta`."""
    delta_attr = (
        "predicted_vs_pre_delta"
        if compared_against == "official_pre"
        else "predicted_vs_post_delta"
    )

    errors = []
    missing = []
    for sector in comparison.sectors:
        delta = getattr(sector, delta_attr)
        if delta is None:
            missing.append(sector.sector)
            continue
        errors.append((sector.sector, abs(delta)))

    total = len(comparison.sectors)
    if not errors:
        return OfficialRatingSummary(
            compared_against=compared_against,
            missing_sectors=tuple(missing),
            confidence="insufficient_data",
        )

    average_error = sum(error for _, error in errors) / len(errors)
    closest = min(errors, key=lambda item: item[1])
    furthest = max(errors, key=lambda item: item[1])

    return OfficialRatingSummary(
        compared_against=compared_against,
        average_error=round(average_error, 4),
        maximum_error=round(furthest[1], 4),
        closest_sector=closest[0],
        closest_sector_error=round(closest[1], 4),
        furthest_sector=furthest[0],
        furthest_sector_error=round(furthest[1], 4),
        missing_sectors=tuple(missing),
        confidence=_confidence_for(len(errors), total),
    )
