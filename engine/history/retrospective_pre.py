"""Missed-PRE workflow (Alpha 0.6.6, Part 17-18).

If the user forgot to import PRE before the match, Official POST can still
create/complete the Match Record. If they later reproduce the formation in
Hattrick (generating a new Copy Ratings capture, necessarily under a
*different*, later Hattrick match ID -- reproducing a lineup always creates
a new match), that capture must be offered as a retrospective simulation --
never silently treated as if it were the real, official PRE for the
already-played match.

Part 18's rule stays intact throughout: the record's *official* Match ID is
always the POST/real match ID. A retrospective PRE's own (different) source
match ID is stored alongside it for traceability, but never rewrites the
record's official identity.
"""
from __future__ import annotations

from dataclasses import replace as dc_replace

from engine.history.enums import MatchRecordStatus, OfficialRatingSourceType


def detect_retrospective_pre_candidate(repository, parsed_pre_snapshot):
    parsed_match_id = parsed_pre_snapshot.hattrick_match_id
    if not parsed_match_id:
        return None
    if repository.find_by_match_id(parsed_match_id) is not None:
        return None

    candidates = [
        record for record in repository.list_all()
        if record.official_pre is None
        and record.retrospective_pre is None
        and record.status in (
            MatchRecordStatus.INCOMPLETE,
            MatchRecordStatus.PLAYED_POST_PENDING,
        )
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda record: record.updated_at or "")


def save_as_retrospective_simulation(
    repository,
    record,
    parsed_pre_snapshot,
    confidence="",
    limitation="",
):
    retrospective = dc_replace(
        parsed_pre_snapshot,
        source_type=OfficialRatingSourceType.RETROSPECTIVE_PRE.value,
        source_match_id=parsed_pre_snapshot.hattrick_match_id,
        linked_match_id=record.match_context.official_match_id,
        captured_after_match=True,
        confidence=confidence,
        limitation=limitation,
    )
    updated = record.with_updates(retrospective_pre=retrospective)
    return repository.save(updated)
