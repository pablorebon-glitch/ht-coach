from __future__ import annotations

from enum import Enum


class _StableEnum(str, Enum):
    @classmethod
    def parse(cls, value):
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError as exc:
            raise ValueError(f"invalid {cls.__name__}: {value}") from exc


class CompetitionType(_StableEnum):
    LEAGUE = "league"
    CUP = "cup"
    FRIENDLY = "friendly"
    QUALIFICATION = "qualification"
    TOURNAMENT = "tournament"
    OTHER = "other"
    UNKNOWN = "unknown"


class TeamType(_StableEnum):
    FIRST_TEAM = "first_team"
    YOUTH_TEAM = "youth_team"
    UNKNOWN = "unknown"


class SnapshotStage(_StableEnum):
    PLANNED = "planned"
    SUBMITTED = "submitted"
    PLAYED = "played"
    IMPORTED = "imported"


class HomeAway(_StableEnum):
    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class ScheduleGroup(_StableEnum):
    WEEKEND_COMPETITIVE = "weekend_competitive"
    MIDWEEK_COMPETITIVE = "midweek_competitive"
    FRIENDLY_OR_TRAINING = "friendly_or_training"
    OTHER = "other"
    UNKNOWN = "unknown"


class ComparisonSelectorType(_StableEnum):
    PREVIOUS_MATCH = "previous_match"
    PREVIOUS_LEAGUE_MATCH = "previous_league_match"
    PREVIOUS_CUP_MATCH = "previous_cup_match"
    PREVIOUS_FRIENDLY = "previous_friendly"
    PREVIOUS_FIRST_TEAM_MATCH = "previous_first_team_match"
    PREVIOUS_SAME_COHORT = "previous_same_cohort"
    CUSTOM = "custom"


class HistoricalRatingSource(_StableEnum):
    HT_COACH_PREDICTED = "ht_coach_predicted"
    HATTRICK_OFFICIAL = "hattrick_official"
    IMPORTED = "imported"
    USER_ENTERED = "user_entered"
    UNKNOWN = "unknown"


class SnapshotSource(_StableEnum):
    MATCH_ANALYSIS = "match_analysis"
    IMPORTED = "imported"
    USER_ENTERED = "user_entered"
    UNKNOWN = "unknown"


class MatchRecordStatus(_StableEnum):
    """Alpha 0.6.6, Part 12. Never stored redundantly -- always
    *derived* from a snapshot's existing fields
    (`derive_match_record_status()` in
    `engine/history/match_record_status.py`), so it can never drift out
    of sync with the data it describes."""

    PLANNED = "planned"
    PRE_OFFICIAL_IMPORTED = "pre_official_imported"
    PLAYED_POST_PENDING = "played_post_pending"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    RETROSPECTIVE_PRE_AVAILABLE = "retrospective_pre_available"


class OfficialRatingSourceType(_StableEnum):
    """Alpha 0.6.6, Part 16. An official PRE captured before the match
    and a formation recreated afterward are not equivalent evidence --
    this is the field that keeps that distinction explicit everywhere
    an `OfficialRatingSnapshot` is used."""

    OFFICIAL_PRE = "official_pre"
    RETROSPECTIVE_PRE = "retrospective_pre"
    OFFICIAL_POST = "official_post"
