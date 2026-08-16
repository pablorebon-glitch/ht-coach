"""Record editability policy (Alpha 0.6.6, Part 15).

Records in the active competitive week (or still planned/future) may be
edited normally. Completed historical records are read-only by default --
an explicit "Correct record" action is the only way to change one, and even
then only through that one deliberate path. Never a silent edit to
completed history.
"""
from __future__ import annotations

from engine.history.enums import MatchRecordStatus

_READ_ONLY_BY_DEFAULT = (MatchRecordStatus.COMPLETE,)

EDITABLE_FIELDS = (
    "opponent_name",
    "planned_formation",
    "planned_tactic",
    "planned_attitude",
    "match_date",
    "competition_type",
)


def is_normally_editable(record):
    return record.status not in _READ_ONLY_BY_DEFAULT


def requires_explicit_correction(record):
    return record.status in _READ_ONLY_BY_DEFAULT
