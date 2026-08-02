"""Legacy record migration into the unified workflow (Alpha 0.6.7, Part 20).

Orchestrates everything already built across this sprint into one explicit
migration pass with a report:

- Loading itself is already backward compatible (`HistoricalMatchSnapshot.
  from_dict` defaults every Alpha 0.6.6/0.6.7 field gracefully when absent
  -- see Alpha 0.6.6 Part 21 and this file's own tests).
- The COMPLETE status invariant can never actually be violated by a record
  going through this system, because `MatchRecordStatus` is always derived
  fresh from real evidence (Part 16) rather than stored -- there's nothing
  to "repair" there structurally, but this pass still verifies it
  defensively for every record and reports anything unexpected rather than
  assuming.
- Duplicate detection/reconciliation (Part 17) runs as part of the same
  pass, using the exact same safe-merge rules -- never silently resolving
  an ambiguous group.

Nothing here is destructive beyond what `reconcile_duplicates()` itself
already does (merging safe duplicates); everything else is read-only
verification, always reported explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.history.duplicate_reconciliation import reconcile_duplicates
from engine.history.match_record_status import assert_status_invariants


@dataclass(frozen=True)
class MigrationReport:
    total_records_before: int = 0
    total_records_after: int = 0
    merged_duplicate_groups: int = 0
    unresolved_duplicate_groups: tuple = ()
    status_invariant_violations: tuple = ()

    @property
    def is_clean(self) -> bool:
        return not self.unresolved_duplicate_groups and not self.status_invariant_violations

    def to_dict(self):
        return {
            "total_records_before": self.total_records_before,
            "total_records_after": self.total_records_after,
            "merged_duplicate_groups": self.merged_duplicate_groups,
            "unresolved_duplicate_groups": [
                {
                    "kind": group.kind,
                    "snapshot_ids": [record.snapshot_id for record in group.records],
                    "conflict_reason": group.conflict_reason,
                }
                for group in self.unresolved_duplicate_groups
            ],
            "status_invariant_violations": list(self.status_invariant_violations),
        }


def migrate_to_unified_workflow(repository):
    records_before = repository.list_all()
    total_before = len(records_before)

    reconciliation = reconcile_duplicates(repository)

    violations = []
    for record in repository.list_all():
        try:
            assert_status_invariants(record.status, record.official_post)
        except AssertionError as exc:
            violations.append(f"{record.snapshot_id}: {exc}")

    total_after = len(repository.list_all())

    return MigrationReport(
        total_records_before=total_before,
        total_records_after=total_after,
        merged_duplicate_groups=reconciliation.merged_count,
        unresolved_duplicate_groups=reconciliation.unresolved_groups,
        status_invariant_violations=tuple(violations),
    )
