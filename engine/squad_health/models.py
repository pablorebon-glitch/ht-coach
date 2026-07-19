from dataclasses import dataclass, field
from enum import Enum


class AvailabilityStatus(Enum):
    AVAILABLE = "AVAILABLE"
    BRUISED = "BRUISED"
    INJURED = "INJURED"
    SUSPENDED = "SUSPENDED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AvailabilityRecord:
    player_id: str
    player_name: str
    status: AvailabilityStatus
    injury_value: float | None = None
    eligible_for_selection: bool = True
    reason_key: str = "availability.reason.available"
    severity: str = "none"
    estimated_absence_value: float | None = None
    source_field: str = "Lesiones"
    source_value: str = ""


@dataclass(frozen=True)
class UnavailablePlayer:
    player_name: str
    status_label: str
    injury_value: str
    best_position: str
    expected_role: str


@dataclass(frozen=True)
class CoverageResult:
    role: str
    classification: str
    starter: str = ""
    eligible_alternatives: int = 0


@dataclass(frozen=True)
class AvailabilityImpactResult:
    overall_score_difference: float = 0.0
    most_affected_area: str = ""
    replacement_summary: str = ""
    formation_impact: str = ""
    affected_formations: tuple[str, ...] = ()
    affected_sectors: tuple[str, ...] = ()
    unavailable_starter_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class HealthSummaryResult:
    mode_label: str
    available_count: int
    total_count: int
    unavailable_starters: int = 0
    affected_areas: tuple[str, ...] = ()
    severity: str = "None"
    unavailable_players: tuple[UnavailablePlayer, ...] = ()
    coverage: tuple[CoverageResult, ...] = ()
    impact: AvailabilityImpactResult = field(default_factory=AvailabilityImpactResult)
