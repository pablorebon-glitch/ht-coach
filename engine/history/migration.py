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

from dataclasses import dataclass, replace

from engine.history.duplicate_reconciliation import reconcile_duplicates
from engine.history.match_record_status import assert_status_invariants
from engine.history.models import MatchContext


@dataclass(frozen=True)
class MigrationReport:
    total_records_before: int = 0
    total_records_after: int = 0
    merged_duplicate_groups: int = 0
    repaired_display_names: tuple = ()
    unresolved_display_names: tuple = ()
    unresolved_duplicate_groups: tuple = ()
    status_invariant_violations: tuple = ()

    @property
    def is_clean(self) -> bool:
        return (
            not self.unresolved_duplicate_groups
            and not self.unresolved_display_names
            and not self.status_invariant_violations
        )

    def to_dict(self):
        return {
            "total_records_before": self.total_records_before,
            "total_records_after": self.total_records_after,
            "merged_duplicate_groups": self.merged_duplicate_groups,
            "repaired_display_names": list(self.repaired_display_names),
            "unresolved_display_names": list(self.unresolved_display_names),
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

    repaired_names, unresolved_names = repair_contaminated_match_identity_names(
        repository
    )
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
        repaired_display_names=tuple(repaired_names),
        unresolved_display_names=tuple(unresolved_names),
        unresolved_duplicate_groups=reconciliation.unresolved_groups,
        status_invariant_violations=tuple(violations),
    )


def repair_contaminated_match_identity_names(repository):
    repaired = []
    unresolved = []
    for record in repository.list_all():
        opponent_name = (
            record.match_context.opponent.opponent_name
            if record.match_context.opponent
            else ""
        )
        clean_name, reason = _repair_opponent_name(record, opponent_name)
        if clean_name == opponent_name:
            continue
        if clean_name:
            opponent = replace(record.match_context.opponent, opponent_name=clean_name)
            context = MatchContext(
                official_match_id=record.match_context.official_match_id,
                match_date=record.match_context.match_date,
                kickoff_time=record.match_context.kickoff_time,
                season=record.match_context.season,
                round=record.match_context.round,
                competition_type=record.match_context.competition_type,
                match_type=record.match_context.match_type,
                home_away=record.match_context.home_away,
                team_type=record.match_context.team_type,
                opponent=opponent,
                venue=record.match_context.venue,
                snapshot_stage=record.match_context.snapshot_stage,
            )
            repository.save(record.with_updates(match_context=context))
            repaired.append(
                {
                    "snapshot_id": record.snapshot_id,
                    "from": opponent_name,
                    "to": clean_name,
                    "reason": reason,
                }
            )
        else:
            unresolved.append(
                {
                    "snapshot_id": record.snapshot_id,
                    "opponent_name": opponent_name,
                    "reason": reason,
                }
            )
    return tuple(repaired), tuple(unresolved)


def _repair_opponent_name(record, opponent_name):
    from engine.history.match_identity import extract_opponent_name_from_match_identity

    repaired = extract_opponent_name_from_match_identity(
        opponent_name,
        "Hit'em up",
    )
    if repaired != (opponent_name or ""):
        return repaired, "formatted_match_identity"

    if " - " not in (opponent_name or ""):
        return opponent_name, ""
    parts = [part.strip() for part in opponent_name.split(" - ") if part.strip()]
    if len(parts) == 4 and parts[0] == parts[2] and parts[1] == parts[3]:
        return parts[0], "duplicated_display_string"

    retrospective = record.retrospective_pre
    retrospective_team = (
        retrospective.team_name.strip()
        if retrospective is not None and retrospective.team_name
        else ""
    )
    if len(parts) == 3 and retrospective_team and parts[2] == retrospective_team:
        return parts[0], "retrospective_source_contamination"

    return "", "ambiguous_display_string"
