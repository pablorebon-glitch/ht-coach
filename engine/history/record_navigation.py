"""Official Match History navigation (Alpha 0.6.6, Parts 13-14).

Unlike the Weekly Planner (Part 7, exactly three restricted contexts),
Official Match History keeps the *full* available match history --
grouped/filtered primarily by Hattrick season number, with previous/current/
next navigation through whatever the current filter selects.
"""
from __future__ import annotations

from dataclasses import dataclass


def list_records(repository, season_number=None, status=None, competition_type=None):
    records = list(repository.list_all())
    if season_number is not None:
        records = [r for r in records if r.ht_season_number == season_number]
    if status is not None:
        records = [r for r in records if r.status == status]
    if competition_type is not None:
        target = getattr(competition_type, "value", competition_type)
        records = [
            r for r in records
            if getattr(r.match_context.competition_type, "value", r.match_context.competition_type)
            == target
        ]
    # Alpha 0.6.7, Part 15: unknown dates always sort after every dated
    # record, and never reorder randomly between runs -- `snapshot_id`
    # is an explicit, stable tiebreaker rather than relying on
    # whatever order the repository happens to return.
    records.sort(
        key=lambda r: (
            bool(r.match_context.match_date),
            r.match_context.match_date or "",
            r.snapshot_id,
        ),
        reverse=True,
    )
    return records


def available_seasons(repository):
    seasons = {
        record.ht_season_number
        for record in repository.list_all()
        if record.ht_season_number is not None
    }
    return tuple(sorted(seasons, reverse=True))


@dataclass(frozen=True)
class RecordNavigationContext:
    record: object
    index: int
    total: int
    can_go_previous: bool
    can_go_next: bool


def navigate_records(records, current_snapshot_id=None, direction="current"):
    """Navigates within an already-filtered/sorted list (see
    `list_records`, newest-first by convention).

    Alpha 0.6.7, Part 15 fix: "Partido anterior" means chronologically
    *older*, and "Partido siguiente" means chronologically *newer* --
    those are semantic directions, not raw array-index directions.
    Since `records` is newest-first, index 0 is the newest date, so
    moving to an *older* record means *incrementing* the index, and
    moving to a *newer* one means *decrementing* it. Getting this
    backwards (treating "previous" as "index - 1") is exactly the bug
    this sprint's brief calls out -- tests must assert on actual dates,
    never on array positions, to catch this class of bug directly.
    """
    if not records:
        return RecordNavigationContext(
            record=None, index=-1, total=0, can_go_previous=False, can_go_next=False
        )

    if current_snapshot_id is None:
        index = 0
    else:
        index = next(
            (i for i, r in enumerate(records) if r.snapshot_id == current_snapshot_id),
            0,
        )

    if direction == "previous":
        index = min(len(records) - 1, index + 1)
    elif direction == "next":
        index = max(0, index - 1)

    return RecordNavigationContext(
        record=records[index],
        index=index,
        total=len(records),
        can_go_previous=index < len(records) - 1,
        can_go_next=index > 0,
    )
