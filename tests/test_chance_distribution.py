import pytest

from models.chance_distribution import ChanceDistribution


def test_distribution_stores_sector_values():

    distribution = ChanceDistribution(
        left=0.25,
        center=0.50,
        right=0.25
    )

    assert distribution.left == 0.25
    assert distribution.center == 0.50
    assert distribution.right == 0.25


def test_distribution_total():

    distribution = ChanceDistribution(
        left=0.25,
        center=0.50,
        right=0.25
    )

    assert distribution.total() == pytest.approx(
        1.0
    )


def test_distribution_can_represent_non_normalized_values():

    distribution = ChanceDistribution(
        left=2.0,
        center=5.0,
        right=3.0
    )

    assert distribution.total() == pytest.approx(
        10.0
    )


def test_distribution_is_deterministic():

    first = ChanceDistribution(
        left=0.25,
        center=0.50,
        right=0.25
    )

    second = ChanceDistribution(
        left=0.25,
        center=0.50,
        right=0.25
    )

    assert first == second