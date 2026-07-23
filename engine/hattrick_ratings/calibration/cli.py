from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.hattrick_ratings.calibration.models import (
    RealMatchCalibrationRecord,
)
from engine.hattrick_ratings.calibration.repository import CalibrationRepository
from engine.hattrick_ratings.calibration.service import RealMatchCalibrationService


def build_parser():
    parser = argparse.ArgumentParser(
        description="Manage real-match Hattrick calibration records."
    )
    parser.add_argument(
        "--store",
        default=".ht_coach_calibration/real_match_records.json",
        help="Calibration record JSON store.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-records")

    add_record = subparsers.add_parser("add-record")
    add_record.add_argument("file")

    validate = subparsers.add_parser("validate-record")
    validate.add_argument("file")

    finalize = subparsers.add_parser("finalize-record")
    finalize.add_argument("record_id")

    recalculate = subparsers.add_parser("recalculate")
    recalculate.add_argument("--model", default="midfield-v1")

    report = subparsers.add_parser("report")
    report.add_argument("--model", default="midfield-v1")

    export = subparsers.add_parser("export")
    export.add_argument("--model", default="midfield-v1")
    export.add_argument("--output", required=True)

    import_command = subparsers.add_parser("import")
    import_command.add_argument("file")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    service = RealMatchCalibrationService(CalibrationRepository(args.store))
    if args.command == "list-records":
        for record in service.list_records():
            print(f"{record.record_id}\t{record.record_status.value}\t{record.match_date}\t{record.formation}")
        return 0
    if args.command == "add-record":
        record = RealMatchCalibrationRecord.from_dict(
            json.loads(Path(args.file).read_text(encoding="utf-8"))
        )
        service.update_record(record)
        print(f"Added: {record.record_id}")
        return 0
    if args.command == "validate-record":
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        records = payload.get("records") if isinstance(payload, dict) else None
        if records is None:
            records = [payload]
        failed = False
        for item in records:
            record = RealMatchCalibrationRecord.from_dict(item)
            issues, quality, reasons = service.validate_record(record)
            print(f"{record.record_id}\tQuality: {quality.value}")
            for issue in issues:
                prefix = "ERROR" if issue.blocking else "WARN"
                print(f"{record.record_id}\t{prefix}: {issue.code}")
            if reasons:
                print(f"{record.record_id}\tReasons: " + ", ".join(reasons))
            failed = failed or any(issue.blocking for issue in issues)
        return 1 if failed else 0
    if args.command == "finalize-record":
        record = service.finalize_record(args.record_id)
        print(f"Finalized: {record.record_id}")
        print(f"Observations: {len(record.observations_by_model_version)}")
        return 0
    if args.command == "recalculate":
        report = service.recalculate_dataset(args.model)
        print_report(report)
        return 0
    if args.command == "report":
        print_report(service.report(args.model))
        return 0
    if args.command == "export":
        payload = service.export_validation_dataset(args.model)
        Path(args.output).write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Exported fixtures: {len(payload['fixtures'])}")
        return 0
    if args.command == "import":
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        result = service.import_validation_dataset(payload)
        print(f"Imported: {result['imported']}")
        print(f"Skipped: {len(result['skipped'])}")
        return 0
    return 2


def print_report(report):
    metrics = report.aggregate_metrics
    print(f"Model Version: {report.model_version}")
    print(f"Dataset Size: {report.dataset_size}")
    print(f"Sample Count: {metrics.sample_count}")
    print(f"Exact Accuracy: {metrics.exact_accuracy:.0%}")
    print(f"Accuracy Within 0.25: {metrics.within_0_25_accuracy:.0%}")
    print(f"Accuracy Within 0.50: {metrics.within_0_50_accuracy:.0%}")
    print(f"Mean Absolute Error: {metrics.mean_absolute_error:.2f}")
    print(f"Median Absolute Error: {metrics.median_absolute_error:.2f}")
    print(f"Signed Bias: {metrics.signed_bias:.2f}")
    print(f"Maximum Error: {metrics.maximum_error:.2f}")
    print(f"Recommendation: {report.recommendation}")
