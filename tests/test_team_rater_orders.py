from types import SimpleNamespace

import pytest

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.position import Position
from models.side import Side

from engine.analyzers.team_rater import (
    TeamRater
)


def create_player():

    return SimpleNamespace(
        name="Test Player",
        form=7,
        goalkeeper=10,
        defending=10,
        playmaking=10,
        winger=10,
        passing=10,
        scoring=10,
        set_pieces=10,
        experience=10
    )


def create_single_player_lineup(
    position,
    side,
    order
):

    player = create_player()

    return Lineup(
        players=[
            LineupPlayer(
                player=player,
                position=position,
                side=side,
                order=order
            )
        ]
    )


def test_normal_order_preserves_base_ratings():

    lineup = create_single_player_lineup(
        Position.WINGER,
        Side.LEFT,
        Order.NORMAL
    )

    ratings = TeamRater.calculate(
        lineup
    )

    assert ratings.midfield == pytest.approx(
        4.5
    )

    assert ratings.left_attack == pytest.approx(
        11.2
    )


def test_offensive_winger_increases_lateral_attack():

    normal_lineup = create_single_player_lineup(
        Position.WINGER,
        Side.LEFT,
        Order.NORMAL
    )

    offensive_lineup = create_single_player_lineup(
        Position.WINGER,
        Side.LEFT,
        Order.OFFENSIVE
    )

    normal_ratings = TeamRater.calculate(
        normal_lineup
    )

    offensive_ratings = TeamRater.calculate(
        offensive_lineup
    )

    assert (
        offensive_ratings.left_attack
        > normal_ratings.left_attack
    )

    assert (
        offensive_ratings.midfield
        < normal_ratings.midfield
    )


def test_defensive_winger_increases_defense():

    normal_lineup = create_single_player_lineup(
        Position.WINGER,
        Side.LEFT,
        Order.NORMAL
    )

    defensive_lineup = create_single_player_lineup(
        Position.WINGER,
        Side.LEFT,
        Order.DEFENSIVE
    )

    normal_ratings = TeamRater.calculate(
        normal_lineup
    )

    defensive_ratings = TeamRater.calculate(
        defensive_lineup
    )

    assert (
        defensive_ratings.left_defense
        > normal_ratings.left_defense
    )

    assert (
        defensive_ratings.left_attack
        < normal_ratings.left_attack
    )


def test_towards_middle_winger_increases_midfield():

    normal_lineup = create_single_player_lineup(
        Position.WINGER,
        Side.LEFT,
        Order.NORMAL
    )

    towards_middle_lineup = (
        create_single_player_lineup(
            Position.WINGER,
            Side.LEFT,
            Order.TOWARDS_MIDDLE
        )
    )

    normal_ratings = TeamRater.calculate(
        normal_lineup
    )

    towards_middle_ratings = (
        TeamRater.calculate(
            towards_middle_lineup
        )
    )

    assert (
        towards_middle_ratings.midfield
        > normal_ratings.midfield
    )

    assert (
        towards_middle_ratings.left_attack
        < normal_ratings.left_attack
    )


def test_order_only_changes_correct_side():

    normal_lineup = create_single_player_lineup(
        Position.WINGER,
        Side.LEFT,
        Order.NORMAL
    )

    offensive_lineup = create_single_player_lineup(
        Position.WINGER,
        Side.LEFT,
        Order.OFFENSIVE
    )

    normal_ratings = TeamRater.calculate(
        normal_lineup
    )

    offensive_ratings = TeamRater.calculate(
        offensive_lineup
    )

    assert (
        offensive_ratings.right_attack
        == normal_ratings.right_attack
    )

    assert (
        offensive_ratings.right_defense
        == normal_ratings.right_defense
    )
    