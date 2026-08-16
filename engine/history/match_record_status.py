"""Match record status derivation (Alpha 0.6.6, Part 12).

`MatchRecordStatus` is never persisted on its own -- it's always computed
fresh from whatever official PRE/POST/retrospective-PRE data and match date
are actually on hand, so it can never drift out of sync with the record it
describes.
"""
from __future__ import annotations

from engine.history.enums import MatchRecordStatus


def derive_match_record_status(
    official_pre=None,
    official_post=None,
    retrospective_pre=None,
    match_date=None,
    today=None,
):
    status = _derive(official_pre, official_post, retrospective_pre, match_date, today)
    assert_status_invariants(status, official_post)
    return status


def assert_status_invariants(status, official_post):
    """Alpha 0.6.7, Part 16's explicit invariant: a record may only be
    COMPLETE when it actually has an Official POST. Called on every
    derivation (not just in tests) so a future code change that
    violates this can never silently ship -- it fails loudly instead."""
    if status == MatchRecordStatus.COMPLETE and official_post is None:
        raise AssertionError(
            "MatchRecordStatus.COMPLETE requires official_post to be present"
        )


def _derive(official_pre, official_post, retrospective_pre, match_date, today):
    has_official_pre = official_pre is not None
    has_retrospective_pre = retrospective_pre is not None
    has_post = official_post is not None
    match_played = (
        match_date is not None and today is not None and today >= match_date
    )

    if has_official_pre and has_post:
        return MatchRecordStatus.COMPLETE
    if has_retrospective_pre and has_post:
        return MatchRecordStatus.RETROSPECTIVE_PRE_AVAILABLE
    if has_post:
        return MatchRecordStatus.INCOMPLETE
    if has_official_pre:
        return (
            MatchRecordStatus.PLAYED_POST_PENDING
            if match_played
            else MatchRecordStatus.PRE_OFFICIAL_IMPORTED
        )
    if has_retrospective_pre:
        return MatchRecordStatus.RETROSPECTIVE_PRE_AVAILABLE
    if match_played:
        return MatchRecordStatus.INCOMPLETE
    return MatchRecordStatus.PLANNED
