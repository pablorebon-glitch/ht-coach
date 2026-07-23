from __future__ import annotations

from datetime import date

from engine.history.enums import CompetitionType, ScheduleGroup
from engine.history.models import MatchCohort


def classify_match_cohort(context) -> MatchCohort:
    competition = context.competition_type
    schedule_group = _schedule_group(competition, context.match_date)
    official_context = bool(context.official_match_id)
    return MatchCohort(
        competition_type=competition,
        team_type=context.team_type,
        schedule_group=schedule_group,
        official_context=official_context,
    )


def _schedule_group(competition: CompetitionType, match_date: str) -> ScheduleGroup:
    if competition == CompetitionType.FRIENDLY:
        return ScheduleGroup.FRIENDLY_OR_TRAINING
    if competition in (CompetitionType.OTHER, CompetitionType.UNKNOWN):
        return ScheduleGroup.UNKNOWN if not match_date else ScheduleGroup.OTHER

    weekday = _weekday(match_date)
    if weekday is None:
        return ScheduleGroup.UNKNOWN
    if weekday in (5, 6):
        return ScheduleGroup.WEEKEND_COMPETITIVE
    if weekday in (1, 2, 3):
        return ScheduleGroup.MIDWEEK_COMPETITIVE
    return ScheduleGroup.OTHER


def _weekday(match_date: str) -> int | None:
    try:
        return date.fromisoformat(str(match_date)[:10]).weekday()
    except ValueError:
        return None
