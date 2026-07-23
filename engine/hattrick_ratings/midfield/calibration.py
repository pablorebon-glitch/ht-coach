from __future__ import annotations

import argparse

from engine.hattrick_ratings.midfield.validation import (
    MidfieldRatingPredictionProvider,
)
from engine.rating_validation.loader import load_rating_validation_dataset
from engine.rating_validation.validator import RatingValidator


def build_parser():
    parser = argparse.ArgumentParser(
        description="Validate Midfield Rating Engine v1 against fixtures."
    )
    parser.add_argument("path", help="Fixture JSON file or directory.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    dataset = load_rating_validation_dataset(args.path)
    report = RatingValidator(
        prediction_provider=MidfieldRatingPredictionProvider()
    ).validate_dataset(dataset)
    metrics = report.per_sector_metrics["midfield"]
    print(f"Fixtures: {report.coverage.fixtures_analyzed}")
    print(f"Comparable: {report.coverage.comparable_fixtures}")
    print(f"Ignored: {report.coverage.fixtures_ignored}")
    print(f"Midfield comparisons: {metrics.comparison_count}")
    print(f"Midfield MAE: {metrics.mean_absolute_error:.2f}")
    print(f"Midfield median AE: {metrics.median_absolute_error:.2f}")
    print(f"Within 0.25: {metrics.within_025_accuracy:.0%}")
    print(f"Within 0.50: {metrics.within_050_accuracy:.0%}")
    print(f"Signed bias: {metrics.mean_signed_error:.2f}")
    print(f"Max error: {metrics.maximum_error:.2f}")
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
