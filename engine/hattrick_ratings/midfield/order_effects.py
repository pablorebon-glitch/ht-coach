from decimal import Decimal

from engine.hattrick_ratings.midfield.models import MidfieldModelParameters


def order_modifier(position, order, parameters: MidfieldModelParameters) -> tuple[Decimal, str | None]:
    position_key = _enum_key(position)
    order_key = _enum_key(order)
    position_modifiers = parameters.order_modifiers.get(position_key, {})
    if order_key in position_modifiers:
        return position_modifiers[order_key], None
    return Decimal("1.00"), "unsupported_order"


def _enum_key(value):
    return getattr(value, "name", getattr(value, "value", str(value)))
