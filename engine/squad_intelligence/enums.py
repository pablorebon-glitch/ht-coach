from __future__ import annotations

from engine.history.enums import _StableEnum


class ClubStrategy(_StableEnum):
    """The only implemented reference strategy this sprint. Represented
    as a typed input (not a constant scattered through rules) so a
    future sprint can make it configurable without redesigning the
    engine -- every rule that cares about strategy reads it from the
    context, never hardcodes SUSTAINABLE_GROWTH."""

    SUSTAINABLE_GROWTH = "sustainable_growth"


class RecommendedRole(_StableEnum):
    KEY_STARTER = "key_starter"
    STARTER = "starter"
    PRIMARY_TRAINEE = "primary_trainee"
    SECONDARY_TRAINEE = "secondary_trainee"
    TACTICAL_SPECIALIST = "tactical_specialist"
    USEFUL_ROTATION = "useful_rotation"
    DEVELOPMENT_PROJECT = "development_project"
    VETERAN_MENTOR = "veteran_mentor"
    DEPTH_PLAYER = "depth_player"
    TRANSFER_CANDIDATE = "transfer_candidate"
    REPLACEABLE = "replaceable"


class ManagementStatus(_StableEnum):
    KEEP = "keep"
    TRAIN = "train"
    MONITOR = "monitor"
    REVIEW_AT_NEXT_SKILL_LEVEL = "review_at_next_skill_level"
    EVALUATE_SALE = "evaluate_sale"
    MAINTAIN_AS_DEPTH = "maintain_as_depth"
    GRADUALLY_REPLACE = "gradually_replace"
    DO_NOT_INVEST_MORE_TRAINING = "do_not_invest_more_training"


class CurrentPerformance(_StableEnum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"
    INSUFFICIENT_DATA = "insufficient_data"


class TrainingPotential(_StableEnum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EXHAUSTED = "exhausted"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_DATA = "insufficient_data"


class TrainingFit(_StableEnum):
    EXCELLENT = "excellent"
    COMPATIBLE = "compatible"
    PARTIAL = "partial"
    NOT_PRIORITIZED = "not_prioritized"
    NO_TRAINING = "no_training"
    UNKNOWN = "unknown"


class SalaryEfficiency(_StableEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    LOW = "low"
    VERY_LOW = "very_low"
    INSUFFICIENT_DATA = "insufficient_data"


class StrategicValue(_StableEnum):
    KEY = "key"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class MilestoneType(_StableEnum):
    REACH_TRAINED_SKILL_LEVEL = "reach_trained_skill_level"
    REVIEW_AT_AGE = "review_at_age"
    REVIEW_AFTER_MATCHES = "review_after_matches"
    REVIEW_AFTER_TRAINING_CYCLE = "review_after_training_cycle"
    REVIEW_WHEN_REPLACEMENT_EXISTS = "review_when_replacement_exists"
    REVIEW_WHEN_SALARY_THRESHOLD_CONTEXT_EXISTS = (
        "review_when_salary_threshold_context_exists"
    )
    NO_MILESTONE = "no_milestone"
    INSUFFICIENT_DATA = "insufficient_data"


class IntelligenceConfidence(_StableEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class StrengthType(_StableEnum):
    STRONG_CURRENT_CONTRIBUTION = "strong_current_contribution"
    EXCELLENT_TRAINING_FIT = "excellent_training_fit"
    FAVORABLE_AGE = "favorable_age"
    USEFUL_SECONDARY_SKILLS = "useful_secondary_skills"
    TACTICAL_VERSATILITY = "tactical_versatility"
    VALUABLE_SPECIALTY = "valuable_specialty"
    LOW_SALARY_RELATIVE_TO_ROLE = "low_salary_relative_to_role"
    HARD_TO_REPLACE = "hard_to_replace"
    FIRST_TEAM_IMPORTANCE = "first_team_importance"


class RiskType(_StableEnum):
    NO_MEANINGFUL_ACTIVE_TRAINING = "no_meaningful_active_training"
    REDUCED_TRAINING_ONLY = "reduced_training_only"
    DECLINING_DEVELOPMENT_RUNWAY = "declining_development_runway"
    HIGH_SALARY_RELATIVE_TO_ROLE = "high_salary_relative_to_role"
    POOR_STAMINA = "poor_stamina"
    POOR_FORM = "poor_form"
    INJURED_OR_UNAVAILABLE = "injured_or_unavailable"
    LIMITED_POSITIONAL_FLEXIBILITY = "limited_positional_flexibility"
    BLOCKED_BY_STRONGER_PLAYERS = "blocked_by_stronger_players"
    NO_CLEAR_SQUAD_ROLE = "no_clear_squad_role"
    MISSING_DATA = "missing_data"


class LimitationType(_StableEnum):
    MISSING_STABLE_PLAYER_ID = "missing_stable_player_id"
    MISSING_SALARY = "missing_salary"
    MISSING_AGE_DAYS = "missing_age_days"
    NO_ACTIVE_TRAINING = "no_active_training"
    NO_HISTORICAL_APPEARANCES = "no_historical_appearances"
    NO_POSITIONAL_SCORE = "no_positional_score"
    UNAVAILABLE_CURRENT_ROSTER = "unavailable_current_roster"
    UNSUPPORTED_SPECIALTY = "unsupported_specialty"
    INCOMPLETE_SKILLS = "incomplete_skills"
