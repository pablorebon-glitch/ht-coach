from types import SimpleNamespace

import pytest

from engine.performance.player_performance import (
    PlayerPerformance
)


def create_player(form):

    return SimpleNamespace(
        form=form,
        playmaking=10
    )


def test_form_factor_is_neutral_at_form_7():

    factor = PlayerPerformance.form_factor(7)

    assert factor == pytest.approx(1.0)


def test_form_factor_increases_with_form():

    factors = [
        PlayerPerformance.form_factor(form)
        for form in range(1, 9)
    ]

    assert factors == sorted(factors)

    assert len(set(factors)) == len(factors)


@pytest.mark.parametrize(
    "form, expected_factor",
    [
        (1, 0.70),
        (3, 0.80),
        (5, 0.90),
        (7, 1.00),
        (8, 1.05),
    ]
)
def test_expected_form_factors(
    form,
    expected_factor
):

    factor = PlayerPerformance.form_factor(
        form
    )

    assert factor == pytest.approx(
        expected_factor
    )


def test_effective_skill_uses_form_factor():

    player = create_player(
        form=5
    )

    effective_skill = (
        PlayerPerformance.effective_skill(
            player,
            "playmaking"
        )
    )

    assert effective_skill == pytest.approx(
        9.0
    )


def test_effective_skill_grows_with_form():

    scores = []

    for form in range(1, 9):

        player = create_player(
            form=form
        )

        scores.append(
            PlayerPerformance.effective_skill(
                player,
                "playmaking"
            )
        )

    assert scores == sorted(scores)