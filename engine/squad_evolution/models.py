from dataclasses import dataclass, field


AGE_BAND_DEVELOPMENT = "development"
AGE_BAND_PRIME = "prime"
AGE_BAND_EXPERIENCED = "experienced"
AGE_BAND_VETERAN = "veteran"
AGE_BAND_LATE_CAREER = "late_career"
AGE_BAND_UNKNOWN = "unknown"

HORIZON_CURRENT = "current"
HORIZON_SHORT_TERM = "short_term"
HORIZON_MEDIUM_TERM = "medium_term"

TRAINING_UNKNOWN = "unknown"
TRAINING_PLAYMAKING = "playmaking"
TRAINING_DEFENDING = "defending"
TRAINING_SCORING = "scoring"
TRAINING_WINGER = "winger"
TRAINING_GOALKEEPING = "goalkeeping"
TRAINING_PASSING = "passing"
TRAINING_SET_PIECES = "set_pieces"

SUCCESSION_READY_NOW = "ready_now"
SUCCESSION_NEAR_READY = "near_ready"
SUCCESSION_DEVELOPMENT = "development_candidate"
SUCCESSION_EMERGENCY = "emergency_cover"
SUCCESSION_NONE = "no_successor"

RISK_LOW = "low"
RISK_MODERATE = "moderate"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"


@dataclass(frozen=True)
class AgeProfile:
    age_years: int | None
    age_days: int | None
    total_age_days: int | None
    display_age: str
    age_band: str
    source_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgeBandCount:
    age_band: str
    count: int


@dataclass(frozen=True)
class RoleAgeDistribution:
    role: str
    development: int = 0
    prime: int = 0
    experienced: int = 0
    veteran: int = 0
    late_career: int = 0
    unknown: int = 0


@dataclass(frozen=True)
class AgeStructureResult:
    average_squad_age: float | None = None
    median_squad_age: float | None = None
    average_full_strength_xi_age: float | None = None
    average_current_available_xi_age: float | None = None
    youngest_player: str = ""
    oldest_player: str = ""
    age_band_counts: tuple[AgeBandCount, ...] = ()
    role_distribution: tuple[RoleAgeDistribution, ...] = ()


@dataclass(frozen=True)
class SuccessionMapRow:
    role: str
    full_strength_starter: str = ""
    current_available_starter: str = ""
    primary_backup: str = ""
    potential_successor: str = ""
    starter_age_band: str = AGE_BAND_UNKNOWN
    backup_age_band: str = AGE_BAND_UNKNOWN
    successor_age_band: str = AGE_BAND_UNKNOWN
    current_depth: int = 0
    succession_readiness: str = SUCCESSION_NONE
    operational_risk: str = RISK_LOW
    structural_risk: str = RISK_LOW
    temporary_issue: bool = False
    structural_gap: bool = False
    explanation: str = ""


@dataclass(frozen=True)
class DependencyResult:
    key_player: str
    role: str
    dependency_level: str
    current_impact: str
    structural_impact: str
    successor_status: str
    reason: str


@dataclass(frozen=True)
class DevelopmentCandidateResult:
    player_name: str
    current_best_role: str
    age_band: str
    current_squad_status: str
    potential_future_role: str
    development_classification: str
    formation_usage: str
    training_alignment: str
    current_availability: str
    strengths: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrainingAlignmentResult:
    current_training: str = TRAINING_UNKNOWN
    alignment: str = "unknown"
    strongly_supports: tuple[str, ...] = ()
    partially_supports: tuple[str, ...] = ()
    not_addressed: tuple[str, ...] = ()
    players_benefiting: tuple[str, ...] = ()
    structural_gaps_not_addressed: tuple[str, ...] = ()
    explanation: str = ""


@dataclass(frozen=True)
class IdentityContinuityResult:
    current_identity: str = ""
    continuity: str = "watch"
    reason: str = ""
    key_contributors: tuple[str, ...] = ()


@dataclass(frozen=True)
class PriorityRiskResult:
    priority: int
    role: str
    planning_horizon: str
    risk_level: str
    risk_type: str
    reason: str
    internal_solution_status: str
    training_support: str
    key_dependency: str = ""


@dataclass(frozen=True)
class PlayerEvolutionDetail:
    player_name: str
    current_role: str = ""
    current_squad_status: str = ""
    age_band: str = AGE_BAND_UNKNOWN
    formation_usage: str = ""
    current_availability: str = ""
    potential_future_role: str = ""
    succession_relationships: tuple[str, ...] = ()
    training_alignment: str = ""
    dependency_level: str = RISK_LOW
    strengths: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class SquadEvolutionResult:
    planning_horizon: str = HORIZON_CURRENT
    current_training: str = TRAINING_UNKNOWN
    summary_sentences: tuple[str, ...] = ()
    age_structure: AgeStructureResult = field(default_factory=AgeStructureResult)
    succession_map: tuple[SuccessionMapRow, ...] = ()
    dependencies: tuple[DependencyResult, ...] = ()
    development_candidates: tuple[DevelopmentCandidateResult, ...] = ()
    training_alignment: TrainingAlignmentResult = field(
        default_factory=TrainingAlignmentResult
    )
    identity_continuity: IdentityContinuityResult = field(
        default_factory=IdentityContinuityResult
    )
    priority_risks: tuple[PriorityRiskResult, ...] = ()
    player_details: tuple[PlayerEvolutionDetail, ...] = ()
