import pytest

from models.contribution import Contribution
from models.order import Order
from models.position import Position
from models.side import Side

from engine.orders.order_modifier import (
    OrderModifier
)


def create_contribution():

    return Contribution(
        left_defense=10,
        central_defense=10,
        right_defense=10,
        midfield=10,
        left_attack=10,
        central_attack=10,
        right_attack=10
    )


def test_normal_order_does_not_change_contribution():

    contribution = create_contribution()

    result = OrderModifier.apply(
        contribution,
        Position.WINGER,
        Side.LEFT,
        Order.NORMAL
    )

    assert result == contribution


def test_unsupported_order_does_not_change_contribution():

    contribution = create_contribution()

    result = OrderModifier.apply(
        contribution,
        Position.GOALKEEPER,
        Side.CENTER,
        Order.OFFENSIVE
    )

    assert result == contribution


def test_left_winger_offensive_modifies_left_side():

    contribution = create_contribution()

    result = OrderModifier.apply(
        contribution,
        Position.WINGER,
        Side.LEFT,
        Order.OFFENSIVE
    )

    assert result.left_attack == pytest.approx(
        12.5
    )

    assert result.right_attack == pytest.approx(
        10.0
    )


def test_right_winger_offensive_modifies_right_side():

    contribution = create_contribution()

    result = OrderModifier.apply(
        contribution,
        Position.WINGER,
        Side.RIGHT,
        Order.OFFENSIVE
    )

    assert result.right_attack == pytest.approx(
        12.5
    )

    assert result.left_attack == pytest.approx(
        10.0
    )


def test_defensive_winger_increases_defense():

    contribution = create_contribution()

    result = OrderModifier.apply(
        contribution,
        Position.WINGER,
        Side.LEFT,
        Order.DEFENSIVE
    )

    assert (
        result.left_defense
        > contribution.left_defense
    )

    assert (
        result.central_defense
        > contribution.central_defense
    )

    assert (
        result.left_attack
        < contribution.left_attack
    )


def test_towards_middle_winger_increases_midfield():

    contribution = create_contribution()

    result = OrderModifier.apply(
        contribution,
        Position.WINGER,
        Side.LEFT,
        Order.TOWARDS_MIDDLE
    )

    assert (
        result.midfield
        > contribution.midfield
    )

    assert (
        result.left_attack
        < contribution.left_attack
    )


def test_defensive_inner_midfielder_trades_attack_for_defense():

    contribution = create_contribution()

    result = OrderModifier.apply(
        contribution,
        Position.INNER_MIDFIELDER,
        Side.CENTER,
        Order.DEFENSIVE
    )

    assert (
        result.central_defense
        > contribution.central_defense
    )

    assert (
        result.central_attack
        < contribution.central_attack
    )


def test_defensive_forward_trades_attack_for_midfield():

    contribution = create_contribution()

    result = OrderModifier.apply(
        contribution,
        Position.FORWARD,
        Side.CENTER,
        Order.DEFENSIVE
    )

    assert (
        result.midfield
        > contribution.midfield
    )

    assert (
        result.central_attack
        < contribution.central_attack
    )


def test_towards_wing_forward_uses_player_side():

    contribution = create_contribution()

    left_result = OrderModifier.apply(
        contribution,
        Position.FORWARD,
        Side.LEFT,
        Order.TOWARDS_WING
    )

    right_result = OrderModifier.apply(
        contribution,
        Position.FORWARD,
        Side.RIGHT,
        Order.TOWARDS_WING
    )

    assert left_result.left_attack == pytest.approx(
        14.0
    )

    assert left_result.right_attack == pytest.approx(
        10.0
    )

    assert right_result.right_attack == pytest.approx(
        14.0
    )

    assert right_result.left_attack == pytest.approx(
        10.0
    )