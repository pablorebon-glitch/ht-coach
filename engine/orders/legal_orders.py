"""Canonical individual-order legality policy.

The optimizer, interactive workspace, and Formation Board all route
through this module so a slot cannot be legal in one layer and illegal
in another.
"""
from __future__ import annotations

from dataclasses import dataclass

from models.order import Order
from models.position import Position
from models.side import Side


@dataclass(frozen=True)
class OrderConfiguration:
    order: Order
    order_side: Side | None = None


_BASE_ALLOWED_CONFIGURATIONS = {
    Position.GOALKEEPER: (
        OrderConfiguration(Order.NORMAL),
    ),
    Position.CENTRAL_DEFENDER: (
        OrderConfiguration(Order.NORMAL),
        OrderConfiguration(Order.OFFENSIVE),
        OrderConfiguration(Order.TOWARDS_WING, Side.LEFT),
        OrderConfiguration(Order.TOWARDS_WING, Side.RIGHT),
    ),
    Position.WING_BACK: (
        OrderConfiguration(Order.NORMAL),
        OrderConfiguration(Order.OFFENSIVE),
        OrderConfiguration(Order.DEFENSIVE),
        OrderConfiguration(Order.TOWARDS_MIDDLE),
    ),
    Position.INNER_MIDFIELDER: (
        OrderConfiguration(Order.NORMAL),
        OrderConfiguration(Order.OFFENSIVE),
        OrderConfiguration(Order.DEFENSIVE),
        OrderConfiguration(Order.TOWARDS_WING, Side.LEFT),
        OrderConfiguration(Order.TOWARDS_WING, Side.RIGHT),
    ),
    Position.WINGER: (
        OrderConfiguration(Order.NORMAL),
        OrderConfiguration(Order.OFFENSIVE),
        OrderConfiguration(Order.DEFENSIVE),
        OrderConfiguration(Order.TOWARDS_MIDDLE),
    ),
    Position.FORWARD: (
        OrderConfiguration(Order.NORMAL),
        OrderConfiguration(Order.DEFENSIVE),
        OrderConfiguration(Order.TOWARDS_WING, Side.LEFT),
        OrderConfiguration(Order.TOWARDS_WING, Side.RIGHT),
    ),
}

_CENTRAL_FORWARD_CONFIGURATIONS = (
    OrderConfiguration(Order.NORMAL),
    OrderConfiguration(Order.DEFENSIVE),
)


def base_allowed_configurations():
    return _BASE_ALLOWED_CONFIGURATIONS


def legal_orders_for_slot(
    position,
    side=None,
    formation="",
    tactical_context=None,
):
    """Return the legal order configurations for one tactical slot."""
    normalized_position = _position(position)
    normalized_side = _side(side)
    if (
        normalized_position == Position.FORWARD
        and normalized_side == Side.CENTER
    ):
        return _CENTRAL_FORWARD_CONFIGURATIONS
    return _BASE_ALLOWED_CONFIGURATIONS.get(
        normalized_position,
        _BASE_ALLOWED_CONFIGURATIONS[Position.GOALKEEPER],
    )


def is_legal_order_for_slot(
    position,
    side,
    order,
    order_side=None,
    formation="",
    tactical_context=None,
):
    normalized_order = _order(order)
    normalized_order_side = _optional_side(order_side)
    return any(
        configuration.order == normalized_order
        and configuration.order_side == normalized_order_side
        for configuration in legal_orders_for_slot(
            position,
            side,
            formation,
            tactical_context,
        )
    )


def normal_order_for_slot(
    position,
    side=None,
    formation="",
    tactical_context=None,
):
    configurations = legal_orders_for_slot(
        position,
        side,
        formation,
        tactical_context,
    )
    return next(
        configuration
        for configuration in configurations
        if configuration.order == Order.NORMAL
    )


def _position(value):
    if isinstance(value, Position):
        return value
    raw = getattr(value, "value", value)
    normalized = str(raw or "").strip().upper().replace(" ", "_")
    for position in Position:
        if normalized in (position.name, position.value):
            return position
    return Position.GOALKEEPER


def _side(value):
    if isinstance(value, Side):
        return value
    raw = getattr(value, "value", value)
    normalized = str(raw or "").strip().upper().replace(" ", "_")
    for side in Side:
        if normalized in (side.name, side.value):
            return side
    return Side.CENTER


def _optional_side(value):
    if value in (None, ""):
        return None
    return _side(value)


def _order(value):
    if isinstance(value, Order):
        return value
    raw = getattr(value, "value", value)
    normalized = str(raw or "").strip()
    for order in Order:
        if normalized in (order.name, order.value):
            return order
    return Order.NORMAL
