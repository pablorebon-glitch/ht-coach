from dataclasses import dataclass, field


OBJECTIVE_BALANCED = "balanced"
OBJECTIVE_PROMOTION_PUSH = "promotion_push"
OBJECTIVE_LONG_TERM_DEVELOPMENT = "long_term_development"
OBJECTIVE_SQUAD_RENEWAL = "squad_renewal"
OBJECTIVE_IMMEDIATE_STABILITY = "immediate_stability"

BUDGET_UNSPECIFIED = "unspecified"
BUDGET_RESTRICTED = "restricted"
BUDGET_MODERATE = "moderate"
BUDGET_FLEXIBLE = "flexible"

AGE_STRATEGY_ANY = "any"
AGE_STRATEGY_IMMEDIATE = "immediate_performance"
AGE_STRATEGY_BALANCED = "balanced"
AGE_STRATEGY_TRAINABLE = "trainable"
AGE_STRATEGY_YOUTH = "youth_development"

TRAINING_PREF_ANY = "any"
TRAINING_PREF_PREFER = "prefer_compatible"
TRAINING_PREF_REQUIRE = "require_compatible"

SPECIALTY_NO_PREFERENCE = "no_preference"

URGENCY_CRITICAL = "critical"
URGENCY_HIGH = "high"
URGENCY_MEDIUM = "medium"
URGENCY_LOW = "low"
URGENCY_MONITOR = "monitor"

NEED_IMMEDIATE_STARTER = "immediate_starter"
NEED_STARTER_COMPETITION = "starter_competition"
NEED_ROTATION_DEPTH = "rotation_depth"
NEED_RELIABLE_BACKUP = "reliable_backup"
NEED_SUCCESSION_REPLACEMENT = "succession_replacement"
NEED_DEVELOPMENT_PROSPECT = "development_prospect"
NEED_SPECIALIST = "specialist"
NEED_NONE = "no_transfer_needed"

ACTION_BUY_NOW = "buy_now"
ACTION_RECRUIT_DEVELOP = "recruit_and_develop"
ACTION_DEVELOP_INTERNALLY = "develop_internally"
ACTION_MONITOR = "monitor"
ACTION_NONE = "no_action_required"

INTERNAL_READY = "ready_internal_solution"
INTERNAL_NEAR_READY = "near_ready_internal_solution"
INTERNAL_DEVELOPMENT = "development_path_available"
INTERNAL_EMERGENCY = "emergency_internal_cover_only"
INTERNAL_NONE = "no_internal_solution"
INTERNAL_UNKNOWN = "unknown"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

IMPACT_MAJOR = "major"
IMPACT_MEANINGFUL = "meaningful"
IMPACT_MODERATE = "moderate"
IMPACT_LIMITED = "limited"
IMPACT_UNKNOWN = "unknown"


@dataclass(frozen=True)
class TransferConstraints:
    planning_objective: str = OBJECTIVE_BALANCED
    budget_tier: str = BUDGET_UNSPECIFIED
    preferred_age_strategy: str = AGE_STRATEGY_BALANCED
    training_compatibility_preference: str = TRAINING_PREF_ANY
    specialty_preference: str = SPECIALTY_NO_PREFERENCE


@dataclass(frozen=True)
class SkillRequirement:
    skill: str
    minimum_level: str = ""
    preferred_level: str = ""
    stretch_level: str = ""


@dataclass(frozen=True)
class PlayerProfile:
    position: str
    target_role: str
    age_range: str
    primary_skill: SkillRequirement
    secondary_skills: tuple[SkillRequirement, ...] = ()
    optional_skills: tuple[str, ...] = ()
    specialty_preferences: tuple[str, ...] = ()
    experience_preference: str = ""
    leadership_preference: str = ""
    training_compatibility: str = "unknown"
    formation_compatibility: tuple[str, ...] = ()
    identity_compatibility: str = "identity_neutral"
    availability_expectation: str = "available"
    profile_rationale: str = ""
    tradeoffs: tuple[str, ...] = ()
    confidence: str = CONFIDENCE_MEDIUM


@dataclass(frozen=True)
class ProfileImpactProjection:
    qualitative_impact: str = IMPACT_UNKNOWN
    dimensions: tuple[str, ...] = ()
    no_exact_delta_statement: str = (
        "No exact performance delta is projected for an abstract profile."
    )


@dataclass(frozen=True)
class NoActionScenario:
    current: str = ""
    short_term: str = ""
    medium_term: str = ""


@dataclass(frozen=True)
class TransferNeed:
    need_id: str
    role: str
    position_family: str
    priority_rank: int
    urgency: str
    planning_horizon: str
    need_type: str
    target_squad_role: str
    reason_keys: tuple[str, ...] = ()
    source_risks: tuple[str, ...] = ()
    structural_or_temporary: str = "no_need"
    internal_solution_status: str = INTERNAL_UNKNOWN
    training_support: str = "unknown"
    identity_relevance: str = "identity_neutral"
    formation_relevance: tuple[str, ...] = ()
    recommended_action: str = ACTION_MONITOR
    recommended_profile: PlayerProfile | None = None
    alternative_profiles: tuple[PlayerProfile, ...] = ()
    impact_projection: ProfileImpactProjection = field(
        default_factory=ProfileImpactProjection
    )
    confidence: str = CONFIDENCE_MEDIUM
    confidence_reasons: tuple[str, ...] = ()
    data_limitations: tuple[str, ...] = ()
    no_action_scenario: NoActionScenario = field(default_factory=NoActionScenario)


@dataclass(frozen=True)
class TransferPlanSummary:
    top_priority: str = ""
    structural_need_count: int = 0
    development_need_count: int = 0
    internal_solution_count: int = 0
    critical_dependency_count: int = 0
    selected_planning_objective: str = OBJECTIVE_BALANCED
    summary_sentences: tuple[str, ...] = ()


@dataclass(frozen=True)
class TransferPlanResult:
    constraints: TransferConstraints = field(default_factory=TransferConstraints)
    summary: TransferPlanSummary = field(default_factory=TransferPlanSummary)
    needs: tuple[TransferNeed, ...] = ()
