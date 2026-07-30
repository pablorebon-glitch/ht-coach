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
