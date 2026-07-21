from __future__ import annotations

from dataclasses import dataclass, field

from engine.rating_validation.fixture import FixtureCompleteness
from engine.rating_validation.metrics import ErrorMetrics


@dataclass(frozen=True)
class FixtureValidationSummary:
    fixture_name: str
    match_id: str
    completeness: FixtureCompleteness
    compared_sectors: tuple[str, ...] = ()
    missing_official_sectors: tuple[str, ...] = ()
    missing_predicted_sectors: tuple[str, ...] = ()
    ignored: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationCoverage:
    fixtures_analyzed: int = 0
    fixtures_ignored: int = 0
    comparable_fixtures: int = 0
    possible_comparisons: int = 0
    completed_comparisons: int = 0

    @property
    def comparison_coverage(self) -> float:
        if self.possible_comparisons == 0:
            return 0.0
        return self.completed_comparisons / self.possible_comparisons


@dataclass(frozen=True)
class ValidationReport:
    global_metrics: ErrorMetrics
    per_sector_metrics: dict[str, ErrorMetrics]
    fixture_summaries: tuple[FixtureValidationSummary, ...] = ()
    ignored_fixtures: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    coverage: ValidationCoverage = field(default_factory=ValidationCoverage)

    def worst_fixture(self) -> str:
        worst_name = ""
        worst_error = -1.0
        for summary in self.fixture_summaries:
            errors = [
                self.per_sector_metrics[sector].maximum_error
                for sector in summary.compared_sectors
                if sector in self.per_sector_metrics
            ]
            if errors and max(errors) > worst_error:
                worst_error = max(errors)
                worst_name = summary.fixture_name
        return worst_name
