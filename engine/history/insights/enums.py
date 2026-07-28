from __future__ import annotations

from engine.history.enums import _StableEnum


class InsightCategory(_StableEnum):
    SECTOR_PERFORMANCE = "sector_performance"
    FORMATION = "formation"
    TACTIC = "tactic"
    LINEUP = "lineup"
    PLAYER_CONDITION = "player_condition"
    INDIVIDUAL_ORDER = "individual_order"
    PREDICTION = "prediction"
    DATA_QUALITY = "data_quality"
    OVERALL = "overall"


class InsightDirection(_StableEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class InsightConfidence(_StableEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class InsightSeverity(_StableEnum):
    """Visual/priority weight, independent of confidence. A HIGH
    confidence insight can still be a MINOR one (e.g. a single order
    changed), and a LOW confidence insight can still be NOTABLE if it
    touches an important sector."""

    CRITICAL = "critical"
    NOTABLE = "notable"
    MINOR = "minor"


class InsightRelationship(_StableEnum):
    """The causal-language guardrail encoded as data instead of wording.
    Rules must pick one of these rather than writing cautious phrasing
    directly into a message string; the UI/localization layer decides
    how each relationship reads in a given language."""

    OBSERVED = "observed"
    ASSOCIATED_WITH = "associated_with"
    LIKELY_CONTRIBUTOR = "likely_contributor"
    POSSIBLE_CONTRIBUTOR = "possible_contributor"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceType(_StableEnum):
    SECTOR_DELTA = "sector_delta"
    FORMATION_CHANGE = "formation_change"
    MIDFIELDER_COUNT = "midfielder_count"
    DEFENDER_COUNT = "defender_count"
    FORWARD_COUNT = "forward_count"
    INDIVIDUAL_ORDER_CHANGE = "individual_order_change"
    ORDER_SIDE_CHANGE = "order_side_change"
    PLAYER_FORM_CHANGE = "player_form_change"
    PLAYER_STAMINA_CHANGE = "player_stamina_change"
    PLAYER_EXPERIENCE_CHANGE = "player_experience_change"
    PLAYER_SKILL_CHANGE = "player_skill_change"
    TACTIC_CHANGE = "tactic_change"
    TACTIC_LEVEL_CHANGE = "tactic_level_change"
    ATTITUDE_CHANGE = "attitude_change"
    CONFIDENCE_CHANGE = "confidence_change"
    HOME_AWAY_CHANGE = "home_away_change"
    PLAYER_ADDED = "player_added"
    PLAYER_REMOVED = "player_removed"
    PLAYER_POSITION_CHANGE = "player_position_change"
    POSSESSION_CHANGE = "possession_change"
    WIN_PROBABILITY_CHANGE = "win_probability_change"
    EXPECTED_GOALS_CHANGE = "expected_goals_change"
    OPPONENT_EXPECTED_GOALS_CHANGE = "opponent_expected_goals_change"


class DataLimitation(_StableEnum):
    NO_OFFICIAL_RATINGS = "no_official_ratings"
    NO_PLAYER_IDS = "no_player_ids"
    MISSING_FORM = "missing_form"
    MISSING_STAMINA = "missing_stamina"
    MISSING_EXPERIENCE = "missing_experience"
    INCOMPATIBLE_RATING_SCALES = "incompatible_rating_scales"
    INCOMPLETE_LINEUP = "incomplete_lineup"
    IMPORTED_LEGACY_SNAPSHOT = "imported_legacy_snapshot"
    NO_COMPARISON_CANDIDATE = "no_comparison_candidate"
