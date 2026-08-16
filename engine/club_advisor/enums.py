from __future__ import annotations

from engine.history.enums import _StableEnum


class ProjectStatus(_StableEnum):
    """Never computed from a single score -- see dimensions.py for how
    several independent sub-assessments combine into this."""

    EXCELLENT = "excellent"
    HEALTHY = "healthy"
    STABLE = "stable"
    NEEDS_ATTENTION = "needs_attention"
    CRITICAL = "critical"


class PriorityType(_StableEnum):
    MAINTAIN_CURRENT_TRAINING = "maintain_current_training"
    INCREASE_POSITIONAL_DEPTH = "increase_positional_depth"
    DEVELOP_SECONDARY_TRAINEES = "develop_secondary_trainees"
    REDUCE_STARTER_DEPENDENCY = "reduce_starter_dependency"
    MONITOR_SALARY_GROWTH = "monitor_salary_growth"
    REVIEW_AGING_VETERANS = "review_aging_veterans"
    IMPROVE_TRAINING_UTILIZATION = "improve_training_utilization"
    ADDRESS_GOALKEEPER_COVERAGE = "address_goalkeeper_coverage"


class ClubStrengthType(_StableEnum):
    TRAINING_FULLY_UTILIZED = "training_fully_utilized"
    EXCELLENT_TRAINEE_PIPELINE = "excellent_trainee_pipeline"
    BALANCED_MIDFIELD = "balanced_midfield"
    GOOD_TACTICAL_FLEXIBILITY = "good_tactical_flexibility"
    HEALTHY_AGE_DISTRIBUTION = "healthy_age_distribution"
    STRONG_POSITIONAL_COVERAGE = "strong_positional_coverage"


class ClubRiskType(_StableEnum):
    ONLY_ONE_GOALKEEPER = "only_one_goalkeeper"
    NO_CENTRAL_DEFENDER_REPLACEMENT = "no_central_defender_replacement"
    PLAYERS_WITHOUT_TRAINING = "players_without_training"
    TOO_MANY_PLAYERS_PER_TRAINING_SLOT = "too_many_players_per_training_slot"
    STARTER_DEPENDENCY = "starter_dependency"
    WEAK_POSITIONAL_DEPTH = "weak_positional_depth"
    POOR_TACTICAL_FLEXIBILITY = "poor_tactical_flexibility"
    HIGH_AGE_CONCENTRATION = "high_age_concentration"


class ClubWarningType(_StableEnum):
    NO_GOALKEEPER_BACKUP = "no_goalkeeper_backup"
    TRAINING_CAPACITY_UNDERUSED = "training_capacity_underused"
    STARTER_HAS_NO_REPLACEMENT = "starter_has_no_replacement"
    PLAYERS_NOT_RECEIVING_TRAINING = "players_not_receiving_training"
    HIGH_EXPERIENCE_CONCENTRATION = "high_experience_concentration"
    LOW_POSITIONAL_FLEXIBILITY = "low_positional_flexibility"
    REDUCED_TEMPORARY_AVAILABILITY = "reduced_temporary_availability"
    PRIORITY_TRAINEES_MISSING_TRAINING = "priority_trainees_missing_training"
    TRAINING_SLOT_COMPETITION = "training_slot_competition"
    UNUSED_TRAINING_CAPACITY = "unused_training_capacity"
    TRAINING_PLAN_DEVIATION = "training_plan_deviation"


class ClubConfidence(_StableEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class ClubLimitationType(_StableEnum):
    FINANCIAL_DATA_UNAVAILABLE = "financial_data_unavailable"
    LEAGUE_COMPARISON_UNAVAILABLE = "league_comparison_unavailable"
    TRANSFER_MARKET_UNAVAILABLE = "transfer_market_unavailable"
    SALARY_BUDGET_UNAVAILABLE = "salary_budget_unavailable"
    PROMOTION_TARGET_UNKNOWN = "promotion_target_unknown"
    HISTORICAL_DATA_UNAVAILABLE = "historical_data_unavailable"
    NO_ACTIVE_TRAINING = "no_active_training"
    EMPTY_ROSTER = "empty_roster"


class DepthStatus(_StableEnum):
    NO_REPLACEMENT = "no_replacement"
    ONE_REPLACEMENT = "one_replacement"
    HEALTHY_COMPETITION = "healthy_competition"
    EXCESS_PLAYERS = "excess_players"
    FUTURE_SHORTAGE = "future_shortage"


class SeasonPhase(_StableEnum):
    PRESEASON = "preseason"
    EARLY_SEASON = "early_season"
    MID_SEASON = "mid_season"
    LATE_SEASON = "late_season"
    PROMOTION_STAGE = "promotion_stage"
    OFFSEASON = "offseason"
    UNKNOWN = "unknown"


class PromotionObjective(_StableEnum):
    NOT_A_PRIORITY = "not_a_priority"
    WELCOME_IF_NATURAL = "welcome_if_natural"
    TARGET_THIS_SEASON = "target_this_season"
    MUST_PROMOTE = "must_promote"
    AVOID_PROMOTION = "avoid_promotion"
    UNSPECIFIED = "unspecified"


class CurrentCompetitiveness(_StableEnum):
    DOMINANT = "dominant"
    STRONG = "strong"
    COMPETITIVE = "competitive"
    UNDER_PRESSURE = "under_pressure"
    OUTMATCHED = "outmatched"
    UNKNOWN = "unknown"


class SigningCostCategory(_StableEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


class RecommendationHorizon(_StableEnum):
    THIS_WEEK = "this_week"
    NEXT_MATCHES = "next_matches"
    CURRENT_SEASON = "current_season"
    BEFORE_PROMOTION = "before_promotion"
    NEXT_SEASON = "next_season"
    LONG_TERM = "long_term"
    WHEN_CONDITION_CHANGES = "when_condition_changes"
    NO_ACTION_REQUIRED = "no_action_required"


class StrategicNeed(_StableEnum):
    """Answers "how important is it for the club to address this area
    eventually?" -- independent of OperationalUrgency (see
    urgency.py's documented policy for why the two must never be
    computed from one another)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
    INSUFFICIENT_DATA = "insufficient_data"


class OperationalUrgency(_StableEnum):
    """Answers "how soon must the club act?" -- see StrategicNeed."""

    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEFERRED = "deferred"
    NONE = "none"
    INSUFFICIENT_DATA = "insufficient_data"


class PromotionReadiness(_StableEnum):
    READY = "ready"
    NEARLY_READY = "nearly_ready"
    DEVELOPING = "developing"
    NOT_READY = "not_ready"
    NOT_EVALUATED = "not_evaluated"


class ActionType(_StableEnum):
    ACT_NOW = "act_now"
    MAINTAIN = "maintain"
    MONITOR = "monitor"
    PREPARE = "prepare"
    REEVALUATE = "reevaluate"
    DEFER = "defer"
    NO_ACTION = "no_action"
