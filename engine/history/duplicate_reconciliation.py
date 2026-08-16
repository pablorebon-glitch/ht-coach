"""Duplicate record reconciliation (Alpha 0.6.7, Part 17).

Fixes existing duplicates like "two CA Chaco records" -- deterministic
detection using, in order of strength: (1) same official Match ID, (2) same
internal canonical record ID (trivial -- the same object), (3) same
opponent/date/competitive week with overlapping PRE/POST evidence. Safe
duplicates are merged automatically, preserving the richest non-conflicting
metadata into one canonical record. Ambiguous ones are never silently
merged -- they come back in the report for explicit resolution.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from engine.history.models import MatchContext


@dataclass(frozen=True)
class DuplicateGroup:
    kind: str
    records: tuple
    can_auto_merge: bool
    conflict_reason: str = ""


@dataclass(frozen=True)
class ReconciliationReport:
    merged_groups: tuple = ()
    unresolved_groups: tuple = ()

    @property
    def merged_count(self) -> int:
        return len(self.merged_groups)

    @property
    def unresolved_count(self) -> int:
        return len(self.unresolved_groups)


def find_duplicate_groups(repository):
    records = list(repository.list_all())
    groups = []
    grouped_ids = set()

    by_match_id = {}
    for record in records:
        match_id = record.match_context.official_match_id
        if match_id:
            by_match_id.setdefault(match_id, []).append(record)
    for match_id, group in by_match_id.items():
        if len(group) > 1:
            groups.append(_build_group("official_match_id", group))
            grouped_ids.update(r.snapshot_id for r in group)

    remaining = [r for r in records if r.snapshot_id not in grouped_ids]
    partial_grouped_ids = set()
    partials = [
        record for record in remaining
        if _is_partial_official_import_record(record)
    ]
    for partial in partials:
        opponent = _normalized_opponent_name(partial)
        if not opponent:
            continue
        candidates = [
            record for record in remaining
            if record.snapshot_id != partial.snapshot_id
            and not _is_partial_official_import_record(record)
            and _normalized_opponent_name(record) == opponent
            and _has_canonical_match_metadata(record)
        ]
        if len(candidates) == 1:
            group = (candidates[0], partial)
            groups.append(_build_group("partial_official_import", group))
            partial_grouped_ids.update(r.snapshot_id for r in group)
        elif len(candidates) > 1:
            group = tuple(candidates) + (partial,)
            groups.append(
                DuplicateGroup(
                    kind="partial_official_import",
                    records=group,
                    can_auto_merge=False,
                    conflict_reason="ambiguous_partial_official_import",
                )
            )
            partial_grouped_ids.update(r.snapshot_id for r in group)

    remaining = [
        r for r in remaining
        if r.snapshot_id not in partial_grouped_ids
    ]
    by_opponent_week = {}
    for record in remaining:
        opponent = _normalized_opponent_name(record).lower()
        if not opponent:
            continue
        venue = getattr(
            record.match_context.home_away, "value", record.match_context.home_away
        ) or "unknown"
        # Alpha 0.6.7 HF-02, Part 9: venue is part of the weaker
        # identity signal too -- a home leg and an away leg of the
        # same cup tie against the same opponent, same week, must
        # never be mistaken for the same duplicated match just because
        # everything else matches.
        key = (
            opponent,
            record.match_context.match_date or "",
            record.ht_season_number,
            record.ht_season_week,
            venue,
        )
        by_opponent_week.setdefault(key, []).append(record)
    for key, group in by_opponent_week.items():
        if len(group) > 1:
            groups.append(_build_group("opponent_week_evidence", group))

    return tuple(groups)


def _build_group(kind, records):
    can_auto_merge, conflict_reason = _check_mergeable(records)
    return DuplicateGroup(
        kind=kind, records=tuple(records),
        can_auto_merge=can_auto_merge, conflict_reason=conflict_reason,
    )


def _check_mergeable(records):
    pres = [r.official_pre for r in records if r.official_pre is not None]
    posts = [r.official_post for r in records if r.official_post is not None]
    match_ids = {
        r.match_context.official_match_id
        for r in records if r.match_context.official_match_id
    }
    if len(pres) > 1:
        return False, "multiple_official_pre"
    if len(posts) > 1:
        return False, "multiple_official_post"
    if len(match_ids) > 1:
        return False, "conflicting_match_ids"
    return True, ""


def _normalized_opponent_name(record):
    from engine.history.match_identity import extract_opponent_name_from_match_identity

    opponent = record.match_context.opponent
    raw_name = opponent.opponent_name if opponent is not None else ""
    return extract_opponent_name_from_match_identity(raw_name, "Hit'em up").strip()


def _is_partial_official_import_record(record):
    has_official_evidence = (
        record.official_pre is not None
        or record.official_post is not None
        or record.retrospective_pre is not None
    )
    if not has_official_evidence:
        return False
    competition = getattr(
        record.match_context.competition_type,
        "value",
        record.match_context.competition_type,
    )
    venue = getattr(
        record.match_context.home_away,
        "value",
        record.match_context.home_away,
    )
    return (
        not record.lineup
        and not record.match_context.match_date
        and str(competition or "unknown").lower() == "unknown"
        and str(venue or "unknown").lower() == "unknown"
    )


def _has_canonical_match_metadata(record):
    return bool(
        record.match_context.match_date
        or record.lineup
        or record.provisional_identity
        or record.training_cycle_id
        or record.ht_season_number is not None
        or record.ht_season_week is not None
    )


def merge_duplicate_group(repository, group):
    if not group.can_auto_merge:
        raise ValueError(f"cannot auto-merge: {group.conflict_reason}")

    records = sorted(group.records, key=lambda r: r.created_at or "")
    primary = records[0]
    for other in records[1:]:
        primary = _merge_two(primary, other)

    for record in records:
        if record.snapshot_id != primary.snapshot_id:
            repository.delete(record.snapshot_id)
    return repository.save(primary)


def _merge_two(primary, other):
    changes = {}
    if primary.official_pre is None and other.official_pre is not None:
        changes["official_pre"] = other.official_pre
    if primary.official_post is None and other.official_post is not None:
        changes["official_post"] = other.official_post
    if primary.retrospective_pre is None and other.retrospective_pre is not None:
        changes["retrospective_pre"] = other.retrospective_pre
    if not primary.lineup and other.lineup:
        changes["lineup"] = other.lineup
    if primary.ht_season_number is None and other.ht_season_number is not None:
        changes["ht_season_number"] = other.ht_season_number
    if primary.ht_season_week is None and other.ht_season_week is not None:
        changes["ht_season_week"] = other.ht_season_week
    if not primary.training_cycle_id and other.training_cycle_id:
        changes["training_cycle_id"] = other.training_cycle_id
    if not primary.provisional_identity and other.provisional_identity:
        changes["provisional_identity"] = other.provisional_identity
    if not primary.provenance.imported_match_id and other.provenance.imported_match_id:
        changes["provenance"] = replace(
            changes.get("provenance", primary.provenance),
            imported_match_id=other.provenance.imported_match_id,
        )

    official_match_id = (
        other.match_context.official_match_id
        or other.provenance.imported_match_id
        or (
            other.official_pre.hattrick_match_id
            if other.official_pre is not None
            else ""
        )
        or (
            other.official_post.hattrick_match_id
            if other.official_post is not None
            else ""
        )
    )
    if not primary.match_context.official_match_id and official_match_id:
        changes["match_context"] = MatchContext(
            official_match_id=official_match_id,
            match_date=primary.match_context.match_date or other.match_context.match_date,
            kickoff_time=primary.match_context.kickoff_time or other.match_context.kickoff_time,
            season=primary.match_context.season or other.match_context.season,
            round=primary.match_context.round or other.match_context.round,
            competition_type=primary.match_context.competition_type,
            match_type=primary.match_context.match_type or other.match_context.match_type,
            home_away=primary.match_context.home_away,
            team_type=primary.match_context.team_type,
            opponent=primary.match_context.opponent,
            venue=primary.match_context.venue or other.match_context.venue,
            snapshot_stage=primary.match_context.snapshot_stage,
        )

    if changes:
        return primary.with_updates(**changes)
    return primary


def resolve_duplicate_group_manually(repository, group, keep_snapshot_id, merge_metadata=True):
    """Alpha 0.6.7 HF-02, Part 10: the explicit resolution surface for
    a group `merge_duplicate_group()` refused to touch automatically.
    The person picks which record is canonical; everything else in
    the group is removed. When `merge_metadata` is True (the default),
    non-conflicting metadata from the other records is still folded in
    -- the ambiguity was about which record's *conflicting* evidence
    wins, not about discarding everything else. Raises ValueError if
    `keep_snapshot_id` isn't actually one of the group's own records,
    so a caller can never accidentally resolve the wrong group."""
    candidates = {record.snapshot_id: record for record in group.records}
    if keep_snapshot_id not in candidates:
        raise ValueError(f"{keep_snapshot_id!r} is not part of this duplicate group")

    primary = candidates[keep_snapshot_id]
    if merge_metadata:
        for snapshot_id, record in candidates.items():
            if snapshot_id == keep_snapshot_id:
                continue
            primary = _merge_two(primary, record)

    for snapshot_id in candidates:
        if snapshot_id != keep_snapshot_id:
            repository.delete(snapshot_id)
    return repository.save(primary)


def reconcile_duplicates(repository):
    groups = find_duplicate_groups(repository)
    merged = []
    unresolved = []
    for group in groups:
        if group.can_auto_merge:
            merge_duplicate_group(repository, group)
            merged.append(group)
        else:
            unresolved.append(group)
    return ReconciliationReport(merged_groups=tuple(merged), unresolved_groups=tuple(unresolved))
