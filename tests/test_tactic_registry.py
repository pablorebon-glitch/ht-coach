from engine.tactics.tactic_registry import (
    TACTIC_REGISTRY
)

from models.tactic import Tactic


def test_registry_contains_all_tactics():

    assert set(
        TACTIC_REGISTRY
    ) == set(
        Tactic
    )


def test_normal_has_no_special_behavior():

    definition = TACTIC_REGISTRY[
        Tactic.NORMAL
    ]

    assert (
        definition.uses_passing_level
        is False
    )

    assert (
        definition.modifies_distribution
        is False
    )

    assert (
        definition.modifies_chance_volume
        is False
    )

    assert (
        definition.generates_counter_attacks
        is False
    )

    assert (
        definition.modifies_special_events
        is False
    )

    assert (
        definition.converts_normal_chances
        is False
    )


def test_attack_in_middle_is_registered():

    definition = TACTIC_REGISTRY[
        Tactic.ATTACK_IN_MIDDLE
    ]

    assert definition.uses_passing_level

    assert definition.modifies_distribution

    assert definition.modifies_ratings


def test_attack_on_wings_is_registered():

    definition = TACTIC_REGISTRY[
        Tactic.ATTACK_ON_WINGS
    ]

    assert definition.uses_passing_level

    assert definition.modifies_distribution

    assert definition.modifies_ratings


def test_pressing_is_registered():

    definition = TACTIC_REGISTRY[
        Tactic.PRESSING
    ]

    assert definition.modifies_chance_volume


def test_counter_attacks_is_registered():

    definition = TACTIC_REGISTRY[
        Tactic.COUNTER_ATTACKS
    ]

    assert definition.generates_counter_attacks


def test_play_creatively_is_registered():

    definition = TACTIC_REGISTRY[
        Tactic.PLAY_CREATIVELY
    ]

    assert definition.modifies_special_events


def test_long_shots_is_registered():

    definition = TACTIC_REGISTRY[
        Tactic.LONG_SHOTS
    ]

    assert definition.converts_normal_chances