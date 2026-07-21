from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.rating_validation import RatingValidator, load_rating_validation_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate predicted Hattrick ratings.")
    parser.add_argument(
        "path",
        nargs="?",
        default=str(ROOT / "fixtures" / "hattrick"),
        help="JSON fixture file or directory. Defaults to fixtures/hattrick.",
    )
    args = parser.parse_args(argv)

    dataset = load_rating_validation_dataset(args.path)
    report = RatingValidator().validate_dataset(dataset)

    print(f"Fixtures: {report.coverage.fixtures_analyzed}")
    print(f"Comparable: {report.coverage.comparable_fixtures}")
    print(f"Ignored: {report.coverage.fixtures_ignored}")
    print(f"Comparisons: {report.coverage.completed_comparisons}")
    print(f"Coverage: {report.coverage.comparison_coverage:.0%}")
    print(f"Overall MAE: {report.global_metrics.mean_absolute_error:.2f}")
    print(f"Overall RMSE: {report.global_metrics.root_mean_squared_error:.2f}")
    worst = report.worst_fixture() or "Not available"
    print(f"Worst Fixture: {worst}")
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
