from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


PLAYMAKING = "PLAYMAKING"


class TrainingWeekStatus(str, Enum):
    PLANNING = "PLANNING"
    FIRST_MATCH_RECORDED = "FIRST_MATCH_RECORDED"
    SECOND_MATCH_PLANNED = "SECOND_MATCH_PLANNED"
    COMPLETE = "COMPLETE"
    ARCHIVED = "ARCHIVED"


class TrainingPriority(str, Enum):
    REQUIRED_100 = "REQUIRED_100"
    REQUIRED_50 = "REQUIRED_50"
    HIGH_PRIORITY = "HIGH_PRIORITY"
    SECONDARY_PRIORITY = "SECONDARY_PRIORITY"
    NO_PRIORITY = "NO_PRIORITY"
    REST = "REST"


class TrainingSlotClass(str, Enum):
    FULL_TRAINING = "FULL_TRAINING"
    HALF_TRAINING = "HALF_TRAINING"
    NO_TRAINING = "NO_TRAINING"


class MatchRole(str, Enum):
    FIRST_WEEKLY_MATCH = "FIRST_WEEKLY_MATCH"
    SECOND_WEEKLY_MATCH = "SECOND_WEEKLY_MATCH"
    OTHER = "OTHER"


class CompetitionType(str, Enum):
    LEAGUE = "LEAGUE"
    CUP = "CUP"
    FRIENDLY = "FRIENDLY"
    QUALIFICATION = "QUALIFICATION"
    UNKNOWN = "UNKNOWN"


class MatchStatus(str, Enum):
    PLANNED = "PLANNED"
    PLAYED = "PLAYED"


class ExposureConfidence(str, Enum):
    CONFIRMED = "CONFIRMED"
    ASSUMED = "ASSUMED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class CoverageStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    TARGET_MET = "TARGET_MET"
    TARGET_EXCEEDED = "TARGET_EXCEEDED"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


class PlannerState(str, Enum):
    NO_ACTIVE_WEEK = "NO_ACTIVE_WEEK"
    PRIORITIES_INCOMPLETE = "PRIORITIES_INCOMPLETE"
    FIRST_MATCH_NOT_RECORDED = "FIRST_MATCH_NOT_RECORDED"
    READY_TO_PLAN = "READY_TO_PLAN"
    PLANNING = "PLANNING"
    PLAN_READY = "PLAN_READY"
    PLAN_CONFLICTED = "PLAN_CONFLICTED"
    PLAN_ACCEPTED = "PLAN_ACCEPTED"


@dataclass(frozen=True)
class TrainingWeek:
    week_id: str
    start_date: date
    end_date: date
    training_update_date: date
    first_match_date: date
    second_match_date: date
    active_training_type: str = PLAYMAKING
    status: TrainingWeekStatus = TrainingWeekStatus.PLANNING


@dataclass(frozen=True)
class TrainingPriorityRecord:
    player_id: str
    player_name: str
    priority: TrainingPriority = TrainingPriority.NO_PRIORITY
    notes: str = ""


@dataclass(frozen=True)
class TrainingExposure:
    player_id: str
    match_id: str
    position_group: str
    played_minutes: Decimal
    training_factor: Decimal
    effective_training_minutes: Decimal
    source: str
    confidence: ExposureConfidence


@dataclass(frozen=True)
class WeeklyMatchLineupEntry:
    player_id: str
    player_name: str
    slot_id: str
    position: str
    side: str
    order: str = "Normal"
    order_side: str = ""
    played_minutes: Decimal = Decimal("90")


@dataclass(frozen=True)
class WeeklyMatchRecord:
    match_id: str
    match_date: date
    match_role: MatchRole
    opponent_name: str = ""
    competition_type: CompetitionType = CompetitionType.UNKNOWN
    formation: str = ""
    lineup: tuple[WeeklyMatchLineupEntry, ...] = ()
    planned_or_played: MatchStatus = MatchStatus.PLANNED
    source: str = "manual"
    minutes_known: bool = False
    notes: str = ""
    training_exposure_entries: tuple[TrainingExposure, ...] = ()
    # Alpha 0.6.7, Part 19: the canonical Match Record this weekly
    # entry belongs to, when known. Additive and optional -- existing
    # records created before this field existed simply have it empty,
    # and callers fall back to the opponent+date inference
    # (`engine.history.match_deletion.find_linked_weekly_match_records`)
    # when it's not populated.
    linked_match_record_id: str = ""


@dataclass(frozen=True)
class PlayerCoverage:
    player_id: str
    player_name: str
    weekly_target: TrainingPriority
    confirmed_exposure: Decimal = Decimal("0")
    assumed_exposure: Decimal = Decimal("0")
    planned_exposure: Decimal = Decimal("0")
    remaining_exposure: Decimal = Decimal("0")
    target_status: CoverageStatus = CoverageStatus.NOT_STARTED
    source_matches: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlannerConflict:
    code: str
    affected_players: tuple[str, ...] = ()
    affected_constraints: tuple[str, ...] = ()
    explanation_parameters: dict = field(default_factory=dict)
    possible_resolutions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlannerExplanation:
    code: str
    player_id: str = ""
    player_name: str = ""
    parameters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CompetitiveCost:
    baseline_score: float = 0.0
    planned_score: float = 0.0
    score_delta: float = 0.0
    percentage_delta: float = 0.0
    changed_starters: tuple[str, ...] = ()
    rested_players: tuple[str, ...] = ()
    sector_deltas: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TrainingCapacity:
    full_slots: int = 0
    half_slots: int = 0
    effective_player_equivalents: Decimal = Decimal("0")


@dataclass(frozen=True)
class WeeklyPlanResult:
    state: PlannerState
    training_week: TrainingWeek | None = None
    active_training_type: str = PLAYMAKING
    formation: str = ""
    lineup: tuple[WeeklyMatchLineupEntry, ...] = ()
    coverage: tuple[PlayerCoverage, ...] = ()
    conflicts: tuple[PlannerConflict, ...] = ()
    explanations: tuple[PlannerExplanation, ...] = ()
    warnings: tuple[str, ...] = ()
    capacity: TrainingCapacity = field(default_factory=TrainingCapacity)
    competitive_cost: CompetitiveCost = field(default_factory=CompetitiveCost)
