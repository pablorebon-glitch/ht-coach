import pytest

from engine.modifiers.tactic_modifier import (
    TacticModifier
)

from models.contribution import Contribution
from models.tactic import Tactic


@pytest.fixture
def ratings():

    return Contribution(
        left_defense=20,
        central_defense=30,
        right_defense=21,
        midfield=40,
        left_attack=20,
        central_attack=30,
        right_attack=22
    )


def assert_same_ratings(
    result,
    expected
):

    assert (
        result.left_defense
        == pytest.approx(
            expected.left_defense
        )
    )

    assert (
        result.central_defense
        == pytest.approx(
            expected.central_defense
        )
    )

    assert (
        result.right_defense
        == pytest.approx(
            expected.right_defense
        )
    )

    assert (
        result.midfield
        == pytest.approx(
            expected.midfield
        )
    )

    assert (
        result.left_attack
        == pytest.approx(
            expected.left_attack
        )
    )

    assert (
        result.central_attack
        == pytest.approx(
            expected.central_attack
        )
    )

    assert (
        result.right_attack
        == pytest.approx(
            expected.right_attack
        )
    )


def test_normal_tactic_preserves_rating_values(
    ratings
):

    result = TacticModifier.apply(
        ratings,
        Tactic.NORMAL
    )

    assert_same_ratings(
        result,
        ratings
    )


def test_attack_in_middle_is_neutral_in_modifier(
    ratings
):

    result = TacticModifier.apply(
        ratings,
        Tactic.ATTACK_IN_MIDDLE
    )

    assert_same_ratings(
        result,
        ratings
    )


def test_attack_on_wings_is_neutral_in_modifier(
    ratings
):

    result = TacticModifier.apply(
        ratings,
        Tactic.ATTACK_ON_WINGS
    )

    assert_same_ratings(
        result,
        ratings
    )


@pytest.mark.parametrize(
    "tactic",
    list(Tactic)
)
def test_modifier_preserves_rating_values_for_all_tactics(
    ratings,
    tactic
):

    result = TacticModifier.apply(
        ratings,
        tactic
    )

    assert_same_ratings(
        result,
        ratings
    )


@pytest.mark.parametrize(
    "tactic",
    list(Tactic)
)
def test_modifier_does_not_mutate_original_ratings(
    ratings,
    tactic
):

    original_values = (
        ratings.left_defense,
        ratings.central_defense,
        ratings.right_defense,
        ratings.midfield,
        ratings.left_attack,
        ratings.central_attack,
        ratings.right_attack,
    )

    TacticModifier.apply(
        ratings,
        tactic
    )

    current_values = (
        ratings.left_defense,
        ratings.central_defense,
        ratings.right_defense,
        ratings.midfield,
        ratings.left_attack,
        ratings.central_attack,
        ratings.right_attack,
    )

    assert (
        current_values
        == original_values
    )


def test_modifier_is_deterministic(
    ratings
):

    first = TacticModifier.apply(
        ratings,
        Tactic.ATTACK_IN_MIDDLE
    )

    second = TacticModifier.apply(
        ratings,
        Tactic.ATTACK_IN_MIDDLE
    )

    assert_same_ratings(
        first,
        second
    )