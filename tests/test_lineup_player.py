from types import SimpleNamespace

from models.lineup_player import LineupPlayer
from models.order import Order
from models.position import Position
from models.side import Side


def create_player():

    return SimpleNamespace(
        name="Test Player"
    )


def test_lineup_player_defaults_to_center():

    lineup_player = LineupPlayer(
        player=create_player(),
        position=Position.FORWARD
    )

    assert (
        lineup_player.side
        == Side.CENTER
    )


def test_lineup_player_defaults_to_normal_order():

    lineup_player = LineupPlayer(
        player=create_player(),
        position=Position.FORWARD
    )

    assert (
        lineup_player.order
        == Order.NORMAL
    )


def test_lineup_player_defaults_to_no_order_side():

    lineup_player = LineupPlayer(
        player=create_player(),
        position=Position.FORWARD
    )

    assert (
        lineup_player.order_side
        is None
    )


def test_lineup_player_accepts_order_side():

    lineup_player = LineupPlayer(
        player=create_player(),
        position=Position.FORWARD,
        side=Side.CENTER,
        order=Order.TOWARDS_WING,
        order_side=Side.LEFT
    )

    assert (
        lineup_player.order_side
        == Side.LEFT
    )