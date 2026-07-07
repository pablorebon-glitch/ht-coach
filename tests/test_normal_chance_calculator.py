import pytest

from engine.calculators.normal_chance_calculator import (
    NormalChanceCalculator
)


def test_equal_midfields_have_equal_possession():

    result = NormalChanceCalculator.calculate(
        midfield=40,
        opponent_midfield=40
    )

    assert result.possession == pytest.approx(
        0.5
    )


def test_equal_midfields_have_equal_chance_probability():

    result = NormalChanceCalculator.calculate(
        midfield=40,
        opponent_midfield=40
    )

    assert result.chance_probability == pytest.approx(
        0.5
    )

    assert (
        result.opponent_chance_probability
        == pytest.approx(0.5)
    )


def test_chance_probabilities_sum_to_one():

    result = NormalChanceCalculator.calculate(
        midfield=55,
        opponent_midfield=35
    )

    total = (
        result.chance_probability
        + result.opponent_chance_probability
    )

    assert total == pytest.approx(
        1.0
    )


def test_expected_chances_sum_to_ten():

    result = NormalChanceCalculator.calculate(
        midfield=55,
        opponent_midfield=35
    )

    total = (
        result.expected_chances
        + result.opponent_expected_chances
    )

    assert total == pytest.approx(
        10.0
    )


def test_stronger_midfield_gets_more_possession():

    result = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=30
    )

    assert result.possession > 0.5


def test_stronger_midfield_gets_more_chance_probability():

    result = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=30
    )

    assert result.chance_probability > 0.5


def test_stronger_midfield_gets_more_expected_chances():

    result = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=30
    )

    assert (
        result.expected_chances
        > result.opponent_expected_chances
    )


def test_swapping_midfields_swaps_possession():

    first = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=30
    )

    second = NormalChanceCalculator.calculate(
        midfield=30,
        opponent_midfield=50
    )

    assert first.possession == pytest.approx(
        1.0 - second.possession
    )


def test_swapping_midfields_swaps_chance_probability():

    first = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=30
    )

    second = NormalChanceCalculator.calculate(
        midfield=30,
        opponent_midfield=50
    )

    assert (
        first.chance_probability
        == pytest.approx(
            second.opponent_chance_probability
        )
    )

    assert (
        first.opponent_chance_probability
        == pytest.approx(
            second.chance_probability
        )
    )


def test_swapping_midfields_swaps_expected_chances():

    first = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=30
    )

    second = NormalChanceCalculator.calculate(
        midfield=30,
        opponent_midfield=50
    )

    assert (
        first.expected_chances
        == pytest.approx(
            second.opponent_expected_chances
        )
    )

    assert (
        first.opponent_expected_chances
        == pytest.approx(
            second.expected_chances
        )
    )


def test_increasing_midfield_increases_possession():

    low = NormalChanceCalculator.calculate(
        midfield=30,
        opponent_midfield=40
    )

    medium = NormalChanceCalculator.calculate(
        midfield=40,
        opponent_midfield=40
    )

    high = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=40
    )

    assert (
        low.possession
        < medium.possession
        < high.possession
    )


def test_increasing_midfield_increases_chance_probability():

    low = NormalChanceCalculator.calculate(
        midfield=30,
        opponent_midfield=40
    )

    medium = NormalChanceCalculator.calculate(
        midfield=40,
        opponent_midfield=40
    )

    high = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=40
    )

    assert (
        low.chance_probability
        < medium.chance_probability
        < high.chance_probability
    )


def test_increasing_midfield_increases_expected_chances():

    low = NormalChanceCalculator.calculate(
        midfield=30,
        opponent_midfield=40
    )

    medium = NormalChanceCalculator.calculate(
        midfield=40,
        opponent_midfield=40
    )

    high = NormalChanceCalculator.calculate(
        midfield=50,
        opponent_midfield=40
    )

    assert (
        low.expected_chances
        < medium.expected_chances
        < high.expected_chances
    )


def test_zero_midfields_are_balanced():

    result = NormalChanceCalculator.calculate(
        midfield=0,
        opponent_midfield=0
    )

    assert result.possession == pytest.approx(
        0.5
    )

    assert result.chance_probability == pytest.approx(
        0.5
    )

    assert (
        result.opponent_chance_probability
        == pytest.approx(0.5)
    )


def test_zero_midfields_still_produce_ten_expected_chances():

    result = NormalChanceCalculator.calculate(
        midfield=0,
        opponent_midfield=0
    )

    total = (
        result.expected_chances
        + result.opponent_expected_chances
    )

    assert total == pytest.approx(
        10.0
    )


def test_dominant_midfield_gets_almost_all_chances():

    result = NormalChanceCalculator.calculate(
        midfield=100,
        opponent_midfield=1
    )

    assert result.chance_probability > 0.99

    assert result.expected_chances > 9.9


def test_very_weak_midfield_gets_almost_no_chances():

    result = NormalChanceCalculator.calculate(
        midfield=1,
        opponent_midfield=100
    )

    assert result.chance_probability < 0.01

    assert result.expected_chances < 0.1


@pytest.mark.parametrize(
    (
        "midfield",
        "opponent_midfield"
    ),
    [
        (20, 20),
        (30, 40),
        (40, 30),
        (45, 45),
        (50, 35),
        (35, 50),
        (60, 20),
        (20, 60),
    ]
)
def test_all_outputs_are_within_valid_ranges(
    midfield,
    opponent_midfield
):

    result = NormalChanceCalculator.calculate(
        midfield=midfield,
        opponent_midfield=opponent_midfield
    )

    assert 0.0 <= result.possession <= 1.0

    assert (
        0.0
        <= result.chance_probability
        <= 1.0
    )

    assert (
        0.0
        <= result.opponent_chance_probability
        <= 1.0
    )

    assert (
        0.0
        <= result.expected_chances
        <= 10.0
    )

    assert (
        0.0
        <= result.opponent_expected_chances
        <= 10.0
    )


@pytest.mark.parametrize(
    (
        "our_midfield",
        "opponent_midfield"
    ),
    [
        (50, 50),
        (55, 45),
        (60, 40),
        (70, 30),
        (80, 20),
    ]
)
def test_midfield_scenarios_preserve_invariants(
    our_midfield,
    opponent_midfield
):

    result = NormalChanceCalculator.calculate(
        midfield=our_midfield,
        opponent_midfield=opponent_midfield
    )

    assert (
        result.chance_probability
        + result.opponent_chance_probability
        == pytest.approx(1.0)
    )

    assert (
        result.expected_chances
        + result.opponent_expected_chances
        == pytest.approx(10.0)
    )