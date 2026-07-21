from __future__ import annotations

from dataclasses import dataclass

from engine.ratings.sector_rating import CANONICAL_SECTORS
from engine.rating_validation.dataset import RatingValidationDataset
from engine.rating_validation.fixture import RatingPredictionProvider, RatingValidationFixture
from engine.rating_validation.metrics import calculate_error_metrics
from engine.rating_validation.report import (
    FixtureValidationSummary,
    ValidationCoverage,
    ValidationReport,
)


@dataclass
class RatingValidator:
    prediction_provider: RatingPredictionProvider | None = None

    def validate_fixture(self, fixture: RatingValidationFixture) -> ValidationReport:
        return self.validate_dataset(RatingValidationDataset.from_fixtures([fixture]))

    def validate_dataset(self, dataset: RatingValidationDataset) -> ValidationReport:
        global_errors: list[float] = []
        sector_errors: dict[str, list[float]] = {sector: [] for sector in CANONICAL_SECTORS}
        summaries: list[FixtureValidationSummary] = []
        ignored: list[str] = []
        warnings: list[str] = []
        possible = 0
        completed = 0
        comparable_fixtures = 0

        for fixture in dataset:
            prediction = fixture.predicted_ratings
            if prediction is None and self.prediction_provider is not None:
                prediction = self.prediction_provider.predict_fixture(fixture)

            official = fixture.official_hattrick_ratings
            if official is None:
                warning = "missing official ratings"
                warnings.append(f"{fixture.fixture_name}: {warning}")
                ignored.append(fixture.fixture_name)
                summaries.append(
                    FixtureValidationSummary(
                        fixture_name=fixture.fixture_name,
                        match_id=fixture.match_id,
                        completeness=fixture.classified_completeness,
                        ignored=True,
                        warnings=(warning,),
                    )
                )
                continue

            official_present = official.present_sectors()
            possible += len(official_present)
            if prediction is None:
                warning = "missing predicted ratings"
                warnings.append(f"{fixture.fixture_name}: {warning}")
                ignored.append(fixture.fixture_name)
                summaries.append(
                    FixtureValidationSummary(
                        fixture_name=fixture.fixture_name,
                        match_id=fixture.match_id,
                        completeness=fixture.classified_completeness,
                        missing_predicted_sectors=official_present,
                        ignored=True,
                        warnings=(warning,),
                    )
                )
                continue

            compared: list[str] = []
            missing_predicted: list[str] = []
            for sector in CANONICAL_SECTORS:
                official_value = getattr(official, sector)
                predicted_value = getattr(prediction, sector)
                if official_value is None:
                    continue
                if predicted_value is None:
                    missing_predicted.append(sector)
                    continue
                error = float(predicted_value) - float(official_value)
                global_errors.append(error)
                sector_errors[sector].append(error)
                compared.append(sector)
                completed += 1

            fixture_warnings = []
            if missing_predicted:
                fixture_warnings.append("missing predicted sectors")
                warnings.append(
                    f"{fixture.fixture_name}: missing predicted sectors "
                    f"{', '.join(missing_predicted)}"
                )
            ignored_fixture = not compared
            if ignored_fixture:
                ignored.append(fixture.fixture_name)
            else:
                comparable_fixtures += 1

            summaries.append(
                FixtureValidationSummary(
                    fixture_name=fixture.fixture_name,
                    match_id=fixture.match_id,
                    completeness=fixture.classified_completeness,
                    compared_sectors=tuple(compared),
                    missing_official_sectors=official.missing_sectors(),
                    missing_predicted_sectors=tuple(missing_predicted),
                    ignored=ignored_fixture,
                    warnings=tuple(fixture_warnings),
                )
            )

        per_sector = {
            sector: calculate_error_metrics(errors)
            for sector, errors in sector_errors.items()
        }
        coverage = ValidationCoverage(
            fixtures_analyzed=len(dataset),
            fixtures_ignored=len(ignored),
            comparable_fixtures=comparable_fixtures,
            possible_comparisons=possible,
            completed_comparisons=completed,
        )
        return ValidationReport(
            global_metrics=calculate_error_metrics(
                global_errors,
                ignored_count=len(ignored),
            ),
            per_sector_metrics=per_sector,
            fixture_summaries=tuple(summaries),
            ignored_fixtures=tuple(ignored),
            warnings=tuple(warnings),
            coverage=coverage,
        )
