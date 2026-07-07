from dataclasses import dataclass


@dataclass(frozen=True)
class MatchModelConfig:

    # --------------------------------------------------
    # NORMAL CHANCE GENERATION
    # --------------------------------------------------

    normal_chances_per_match: float = 10.0

    midfield_chance_share_exponent: float = 3.0

    # --------------------------------------------------
    # GOAL CONVERSION
    # --------------------------------------------------

    goal_conversion_factor: float = 0.74

    goal_conversion_exponent: float = 3.0

    # --------------------------------------------------
    # SPECIAL EVENTS
    # --------------------------------------------------

    special_event_base_chances: float = 0.50

    special_event_goal_factor: float = 0.35

    # --------------------------------------------------
    # LONG SHOTS
    # --------------------------------------------------

    long_shot_goal_factor: float = 0.55


DEFAULT_MATCH_MODEL_CONFIG = (
    MatchModelConfig()
)