from engine.tactics.tactic_definition import (
    TacticDefinition
)

from models.tactic import Tactic


TACTIC_REGISTRY = {

    Tactic.NORMAL: TacticDefinition(
        tactic=Tactic.NORMAL
    ),

    Tactic.ATTACK_IN_MIDDLE: TacticDefinition(
        tactic=Tactic.ATTACK_IN_MIDDLE,
        uses_passing_level=True,
        modifies_distribution=True,
        modifies_ratings=True
    ),

    Tactic.ATTACK_ON_WINGS: TacticDefinition(
        tactic=Tactic.ATTACK_ON_WINGS,
        uses_passing_level=True,
        modifies_distribution=True,
        modifies_ratings=True
    ),

    Tactic.PRESSING: TacticDefinition(
        tactic=Tactic.PRESSING,
        modifies_chance_volume=True
    ),

    Tactic.COUNTER_ATTACKS: TacticDefinition(
        tactic=Tactic.COUNTER_ATTACKS,
        uses_passing_level=True,
        generates_counter_attacks=True
    ),

    Tactic.PLAY_CREATIVELY: TacticDefinition(
        tactic=Tactic.PLAY_CREATIVELY,
        modifies_special_events=True,
        modifies_ratings=True
    ),

    Tactic.LONG_SHOTS: TacticDefinition(
        tactic=Tactic.LONG_SHOTS,
        converts_normal_chances=True
    ),
}