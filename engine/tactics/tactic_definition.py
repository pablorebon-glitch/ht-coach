from dataclasses import dataclass

from models.tactic import Tactic


@dataclass(frozen=True)
class TacticDefinition:

    tactic: Tactic

    uses_passing_level: bool = False

    modifies_distribution: bool = False

    modifies_ratings: bool = False

    modifies_chance_volume: bool = False

    generates_counter_attacks: bool = False

    modifies_special_events: bool = False

    converts_normal_chances: bool = False