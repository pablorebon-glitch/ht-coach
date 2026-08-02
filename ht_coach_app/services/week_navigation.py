"""Week navigation for the Weekly Planner (Alpha 0.6.6, Part 7).

Exactly three navigable contexts -- previous / current / next. The Planner
is an operational view, not the full historical archive: unrestricted
historical browsing belongs to Official Match History instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from engine.weekly_training.models import MatchRole
from engine.weekly_training.training_week import active_training_week


@dataclass(frozen=True)
class WeekNavigationContext:
    direction: str
    week: object
    first_match: object = None
    second_match: object = None
    is_preview: bool = False
    can_go_previous: bool = False
    can_go_next: bool = False
    training_priorities_available: bool = False
    coverage_available: bool = False


def _matches_for_week(match_records, week):
    if week is None:
        return None, None
    first_match = next(
        (
            record for record in match_records
            if record.match_role == MatchRole.FIRST_WEEKLY_MATCH
            and week.start_date <= record.match_date <= week.end_date
        ),
        None,
    )
    second_match = next(
        (
            record for record in match_records
            if record.match_role == MatchRole.SECOND_WEEKLY_MATCH
            and week.start_date <= record.match_date <= week.end_date
        ),
        None,
    )
    return first_match, second_match


def build_week_navigation_context(state, direction="current"):
    direction = direction if direction in ("previous", "current", "next") else "current"

    current_week = state.active_week
    archived_weeks = tuple(state.archived_weeks or ())
    previous_week = archived_weeks[-1] if archived_weeks else None

    if direction == "previous":
        week = previous_week
        first_match, second_match = _matches_for_week(state.match_records, week)
        return WeekNavigationContext(
            direction="previous",
            week=week,
            first_match=first_match,
            second_match=second_match,
            is_preview=False,
            can_go_previous=False,
            can_go_next=True,
            training_priorities_available=False,
            coverage_available=False,
        )

    if direction == "next":
        week = None
        if current_week is not None:
            preview_date = current_week.training_update_date + timedelta(days=1)
            week = active_training_week(
                today=preview_date,
                training_type=current_week.active_training_type,
            )
        first_match, second_match = _matches_for_week(state.match_records, week)
        return WeekNavigationContext(
            direction="next",
            week=week,
            first_match=first_match,
            second_match=second_match,
            is_preview=True,
            can_go_previous=True,
            can_go_next=False,
            training_priorities_available=False,
            coverage_available=False,
        )

    first_match, second_match = _matches_for_week(state.match_records, current_week)
    return WeekNavigationContext(
        direction="current",
        week=current_week,
        first_match=first_match,
        second_match=second_match,
        is_preview=False,
        can_go_previous=previous_week is not None,
        can_go_next=True,
        training_priorities_available=True,
        coverage_available=True,
    )
