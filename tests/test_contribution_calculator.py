from types import SimpleNamespace

import pytest

from models.side import Side

from engine.calculators.contribution_calculator import (
    ContributionCalculator
)


def create_winger():

    return SimpleNamespace(
        form=7,
        defending=6,
        playmaking=8,
        winger=12,
        passing=7,
        scoring=5
    )


def test_left_winger_only_contributes_to_left_side():

    player = create_winger()

    contribution = ContributionCalculator.calculate(
        player,
        "WINGER",
        Side.LEFT
    )

    assert contribution.left_defense > 0
    assert contribution.left_attack > 0

    assert contribution.right_defense == 0
    assert contribution.right_attack == 0


def test_right_winger_only_contributes_to_right_side():

    player = create_winger()

    contribution = ContributionCalculator.calculate(
        player,
        "WINGER",
        Side.RIGHT
    )

    assert contribution.right_defense > 0
    assert contribution.right_attack > 0

    assert contribution.left_defense == 0
    assert contribution.left_attack == 0


def test_winger_keeps_central_contributions():

    player = create_winger()

    contribution = ContributionCalculator.calculate(
        player,
        "WINGER",
        Side.LEFT
    )

    assert contribution.midfield > 0
    assert contribution.central_defense > 0
    assert contribution.central_attack > 0


def test_form_changes_contribution():

    low_form_player = create_winger()
    high_form_player = create_winger()

    low_form_player.form = 3
    high_form_player.form = 8

    low_contribution = ContributionCalculator.calculate(
        low_form_player,
        "WINGER",
        Side.LEFT
    )

    high_contribution = ContributionCalculator.calculate(
        high_form_player,
        "WINGER",
        Side.LEFT
    )

    assert (
        high_contribution.left_attack
        > low_contribution.left_attack
    )

    assert (
        high_contribution.midfield
        > low_contribution.midfield
    )