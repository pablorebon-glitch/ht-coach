from __future__ import annotations

import argparse
from pathlib import Path

from engine.history.enums import ComparisonSelectorType
from engine.history.previous_match_selector import (
    PreviousMatchSelection,
    PreviousMatchSelector,
)
from engine.history.repository import HistoricalMatchRepository
from engine.history.serialization import (
    repository_payload_to_json,
    snapshots_from_repository_payload,
)
from engine.history.validation import validate_snapshot


def build_parser():
    parser = argparse.ArgumentParser(description="Manage HT Coach historical snapshots.")
    parser.add_argument("--store", default=".ht_coach_history/snapshots.json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("snapshot_id")
    subparsers.add_parser("validate")
    export = subparsers.add_parser("export")
    export.add_argument("--output", required=True)
    import_command = subparsers.add_parser("import")
    import_command.add_argument("file")
    previous = subparsers.add_parser("previous")
    previous.add_argument("snapshot_id")
    previous.add_argument(
        "--selector",
        default=ComparisonSelectorType.PREVIOUS_SAME_COHORT.value,
        choices=[item.value for item in ComparisonSelectorType],
    )
    previous.add_argument("--include-planned", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    repository = HistoricalMatchRepository(args.store)
    if args.command == "list":
        for snapshot in repository.list_all():
            print(
                "\t".join(
                    [
                        snapshot.snapshot_id,
                        snapshot.match_context.match_date,
                        snapshot.match_context.snapshot_stage.value,
                        snapshot.tactical_setup.formation,
                        snapshot.match_context.opponent.opponent_name,
                    ]
                )
            )
        return 0
    if args.command == "inspect":
        snapshot = repository.get(args.snapshot_id)
        if snapshot is None:
            print("Snapshot not found.")
            return 1
        print(repository_payload_to_json([snapshot]))
        return 0
    if args.command == "validate":
        failed = False
        for snapshot in repository.list_all():
            errors = validate_snapshot(snapshot, allow_played_without_official=True)
            for error in errors:
                print(f"{snapshot.snapshot_id}\t{error.field}\t{error.message}")
            failed = failed or bool(errors)
        return 1 if failed else 0
    if args.command == "export":
        Path(args.output).write_text(
            repository_payload_to_json(repository.list_all()),
            encoding="utf-8",
        )
        return 0
    if args.command == "import":
        snapshots = snapshots_from_repository_payload(
            Path(args.file).read_text(encoding="utf-8")
        )
        result = repository.import_snapshots(snapshots)
        print(f"Imported: {result['imported']}")
        print(f"Skipped: {len(result['skipped'])}")
        return 0
    if args.command == "previous":
        current = repository.get(args.snapshot_id)
        if current is None:
            print("Snapshot not found.")
            return 1
        previous = PreviousMatchSelector().select(
            current,
            repository.list_all(),
            PreviousMatchSelection(
                selector_type=args.selector,
                include_planned=args.include_planned,
            ),
        )
        if previous is None:
            print("No previous match found.")
            return 1
        print(previous.snapshot_id)
        return 0
    return 2
