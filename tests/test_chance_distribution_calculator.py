import pytest

from engine.calculators.chance_distribution_calculator import (
    ChanceDistributionCalculator
)

from models.tactic import Tactic


def test_base_distribution_sums_to_one():

    distribution = (
        ChanceDistributionCalculator.calculate()
    )

    assert distribution.total() == pytest.approx(
        1.0
    )


def test_base_distribution_has_expected_values():

    distribution = (
        ChanceDistributionCalculator.calculate()
    )

    assert distribution.left == pytest.approx(
        0.25
    )

    assert distribution.center == pytest.approx(
        0.50
    )

    assert distribution.right == pytest.approx(
        0.25
    )


def test_calculator_returns_new_distribution_each_time():

    first = (
        ChanceDistributionCalculator.calculate()
    )

    second = (
        ChanceDistributionCalculator.calculate()
    )

    assert first is not second

    assert first == second


def test_zero_tactic_level_preserves_normal_distribution():

    distribution = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_IN_MIDDLE,
            tactic_level=0
        )
    )

    assert distribution.left == pytest.approx(
        0.25
    )

    assert distribution.center == pytest.approx(
        0.50
    )

    assert distribution.right == pytest.approx(
        0.25
    )


def test_max_aim_level_uses_maximum_middle_shift():

    distribution = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_IN_MIDDLE,
            tactic_level=20
        )
    )

    assert distribution.left == pytest.approx(
        0.20
    )

    assert distribution.center == pytest.approx(
        0.60
    )

    assert distribution.right == pytest.approx(
        0.20
    )


def test_max_aow_level_uses_maximum_wing_shift():

    distribution = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_ON_WINGS,
            tactic_level=20
        )
    )

    assert distribution.left == pytest.approx(
        0.30
    )

    assert distribution.center == pytest.approx(
        0.40
    )

    assert distribution.right == pytest.approx(
        0.30
    )


def test_higher_aim_level_moves_more_chances_to_center():

    low = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_IN_MIDDLE,
            tactic_level=5
        )
    )

    high = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_IN_MIDDLE,
            tactic_level=15
        )
    )

    assert high.center > low.center

    assert high.left < low.left

    assert high.right < low.right


def test_higher_aow_level_moves_more_chances_to_wings():

    low = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_ON_WINGS,
            tactic_level=5
        )
    )

    high = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_ON_WINGS,
            tactic_level=15
        )
    )

    assert high.left > low.left

    assert high.center < low.center

    assert high.right > low.right


@pytest.mark.parametrize(
    "tactic_level",
    [
        -10,
        -1,
        0,
    ]
)
def test_tactic_level_is_clamped_at_zero(
    tactic_level
):

    distribution = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_IN_MIDDLE,
            tactic_level=tactic_level
        )
    )

    assert distribution.left == pytest.approx(
        0.25
    )

    assert distribution.center == pytest.approx(
        0.50
    )

    assert distribution.right == pytest.approx(
        0.25
    )


@pytest.mark.parametrize(
    "tactic_level",
    [
        20,
        21,
        50,
        100,
    ]
)
def test_tactic_level_is_clamped_at_maximum(
    tactic_level
):

    distribution = (
        ChanceDistributionCalculator.calculate(
            Tactic.ATTACK_IN_MIDDLE,
            tactic_level=tactic_level
        )
    )

    assert distribution.left == pytest.approx(
        0.20
    )

    assert distribution.center == pytest.approx(
        0.60
    )

    assert distribution.right == pytest.approx(
        0.20
    )


@pytest.mark.parametrize(
    "tactic",
    list(Tactic)
)
@pytest.mark.parametrize(
    "tactic_level",
    [
        0,
        5,
        10,
        15,
        20,
    ]
)
def test_tactic_distribution_always_sums_to_one(
    tactic,
    tactic_level
):

    distribution = (
        ChanceDistributionCalculator.calculate(
            tactic,
            tactic_level
        )
    )

    assert distribution.total() == pytest.approx(
        1.0
    )


def test_normal_tactic_ignores_tactic_level():

    low = (
        ChanceDistributionCalculator.calculate(
            Tactic.NORMAL,
            tactic_level=0
        )
    )

    high = (
        ChanceDistributionCalculator.calculate(
            Tactic.NORMAL,
            tactic_level=20
        )
    )

    assert low == high

    assert low.left == pytest.approx(
        0.25
    )

    assert low.center == pytest.approx(
        0.50
    )

    assert low.right == pytest.approx(
        0.25
    )