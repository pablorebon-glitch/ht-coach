from types import SimpleNamespace

from engine.analyzers.team_rater import TeamRater

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.position import Position
from models.side import Side


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


def create_forward(
    order_side
):

    return Lineup(
        players=[
            LineupPlayer(
                player=create_player(),
                position=Position.FORWARD,
                side=Side.CENTER,
                order=Order.TOWARDS_WING,
                order_side=order_side
            )
        ]
    )


def create_inner_midfielder(
    order_side
):

    return Lineup(
        players=[
            LineupPlayer(
                player=create_player(),
                position=Position.INNER_MIDFIELDER,
                side=Side.CENTER,
                order=Order.TOWARDS_WING,
                order_side=order_side
            )
        ]
    )


def test_forward_towards_left_wing_increases_only_left_attack():

    normal = Lineup(
        players=[
            LineupPlayer(
                player=create_player(),
                position=Position.FORWARD
            )
        ]
    )

    towards_left = create_forward(
        Side.LEFT
    )

    normal_ratings = TeamRater.calculate(
        normal
    )

    left_ratings = TeamRater.calculate(
        towards_left
    )

    assert (
        left_ratings.left_attack
        > normal_ratings.left_attack
    )

    assert (
        left_ratings.right_attack
        == normal_ratings.right_attack
    )

    assert (
        left_ratings.central_attack
        < normal_ratings.central_attack
    )


def test_forward_towards_right_wing_increases_only_right_attack():

    normal = Lineup(
        players=[
            LineupPlayer(
                player=create_player(),
                position=Position.FORWARD
            )
        ]
    )

    towards_right = create_forward(
        Side.RIGHT
    )

    normal_ratings = TeamRater.calculate(
        normal
    )

    right_ratings = TeamRater.calculate(
        towards_right
    )

    assert (
        right_ratings.right_attack
        > normal_ratings.right_attack
    )

    assert (
        right_ratings.left_attack
        == normal_ratings.left_attack
    )

    assert (
        right_ratings.central_attack
        < normal_ratings.central_attack
    )


def test_inner_midfielder_towards_left_wing_increases_only_left_attack():

    normal = Lineup(
        players=[
            LineupPlayer(
                player=create_player(),
                position=Position.INNER_MIDFIELDER
            )
        ]
    )

    towards_left = create_inner_midfielder(
        Side.LEFT
    )

    normal_ratings = TeamRater.calculate(
        normal
    )

    left_ratings = TeamRater.calculate(
        towards_left
    )

    assert (
        left_ratings.left_attack
        > normal_ratings.left_attack
    )

    assert (
        left_ratings.right_attack
        == normal_ratings.right_attack
    )

    assert (
        left_ratings.midfield
        < normal_ratings.midfield
    )


def test_inner_midfielder_towards_right_wing_increases_only_right_attack():

    normal = Lineup(
        players=[
            LineupPlayer(
                player=create_player(),
                position=Position.INNER_MIDFIELDER
            )
        ]
    )

    towards_right = create_inner_midfielder(
        Side.RIGHT
    )

    normal_ratings = TeamRater.calculate(
        normal
    )

    right_ratings = TeamRater.calculate(
        towards_right
    )

    assert (
        right_ratings.right_attack
        > normal_ratings.right_attack
    )

    assert (
        right_ratings.left_attack
        == normal_ratings.left_attack
    )

    assert (
        right_ratings.midfield
        < normal_ratings.midfield
    )


def test_normal_order_ignores_order_side():

    normal_without_side = Lineup(
        players=[
            LineupPlayer(
                player=create_player(),
                position=Position.FORWARD,
                order=Order.NORMAL
            )
        ]
    )

    normal_with_side = Lineup(
        players=[
            LineupPlayer(
                player=create_player(),
                position=Position.FORWARD,
                order=Order.NORMAL,
                order_side=Side.LEFT
            )
        ]
    )

    first_ratings = TeamRater.calculate(
        normal_without_side
    )

    second_ratings = TeamRater.calculate(
        normal_with_side
    )

    assert (
        first_ratings
        == second_ratings
    )