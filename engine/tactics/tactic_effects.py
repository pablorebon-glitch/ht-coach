from dataclasses import dataclass

from engine.calculators.chance_distribution_calculator import (
    ChanceDistribution
)


@dataclass
class TacticEffects:

    ratings: object

    our_distribution: ChanceDistribution

    opponent_distribution: ChanceDistribution

    our_chance_multiplier: float = 1.0

    opponent_chance_multiplier: float = 1.0

    counter_attack_chances: float = 0.0

    special_event_multiplier: float = 1.0

    long_shot_conversion_rate: float = 0.0