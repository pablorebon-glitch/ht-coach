import pytest

from engine.modifiers.tactic_chance_modifier import (
    TacticChanceModifier
)

from models.chance_distribution import ChanceDistribution
from models.tactic import Tactic


@pytest.fixture
def base_distribution():

    return ChanceDistribution(
        left=0.25,
        center=0.50,
        right=0.25
    )


def test_normal_preserves_distribution(
    base_distribution
):

    result = TacticChanceModifier.apply(
        base_distribution,
        Tactic.NORMAL
    )

    assert result == base_distribution


def test_normal_returns_new_distribution(
    base_distribution
):

    result = TacticChanceModifier.apply(
        base_distribution,
        Tactic.NORMAL
    )

    assert result is not base_distribution


def test_attack_in_middle_increases_center_share(
    base_distribution
):

    result = TacticChanceModifier.apply(
        base_distribution,
        Tactic.ATTACK_IN_MIDDLE
    )

    assert (
        result.center
        > base_distribution.center
    )


def test_attack_in_middle_reduces_wing_shares(
    base_distribution
):

    result = TacticChanceModifier.apply(
        base_distribution,
        Tactic.ATTACK_IN_MIDDLE
    )

    assert result.left < base_distribution.left

    assert result.right < base_distribution.right


def test_attack_on_wings_increases_wing_shares(
    base_distribution
):

    result = TacticChanceModifier.apply(
        base_distribution,
        Tactic.ATTACK_ON_WINGS
    )

    assert result.left > base_distribution.left

    assert result.right > base_distribution.right


def test_attack_on_wings_reduces_center_share(
    base_distribution
):

    result = TacticChanceModifier.apply(
        base_distribution,
        Tactic.ATTACK_ON_WINGS
    )

    assert (
        result.center
        < base_distribution.center
    )


@pytest.mark.parametrize(
    "tactic",
    [
        Tactic.NORMAL,
        Tactic.ATTACK_IN_MIDDLE,
        Tactic.ATTACK_ON_WINGS,
    ]
)
def test_all_distributions_sum_to_one(
    base_distribution,
    tactic
):

    result = TacticChanceModifier.apply(
        base_distribution,
        tactic
    )

    assert result.total() == pytest.approx(
        1.0
    )


def test_modifier_does_not_mutate_original_distribution(
    base_distribution
):

    TacticChanceModifier.apply(
        base_distribution,
        Tactic.ATTACK_IN_MIDDLE
    )

    assert base_distribution == ChanceDistribution(
        left=0.25,
        center=0.50,
        right=0.25
    )