from dataclasses import dataclass


@dataclass(frozen=True)
class MatchModelConfig:

    # --------------------------------------------------
    # MIDFIELD / CHANCE CREATION
    # --------------------------------------------------

    midfield_chance_share_exponent: float = 3.0

    exclusive_chances_per_team: float = 5.0

    shared_chances: float = 5.0

    # --------------------------------------------------
    # NORMAL CHANCE CONVERSION
    # --------------------------------------------------

    goal_conversion_factor: float = 0.74

    # --------------------------------------------------
    # LONG SHOTS
    # --------------------------------------------------

    long_shot_goal_factor: float = 0.55

    # --------------------------------------------------
    # SPECIAL EVENTS / PLAY CREATIVELY
    # --------------------------------------------------

    special_event_base_chances: float = 0.50

    special_event_goal_factor: float = 0.35