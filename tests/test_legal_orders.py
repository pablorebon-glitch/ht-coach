from engine.orders.legal_orders import is_legal_order_for_slot
from engine.orders.legal_orders import legal_orders_for_slot
from engine.orders.legal_orders import normal_order_for_slot
from models.order import Order
from models.position import Position
from models.side import Side


def _pairs(configurations):
    return {
        (configuration.order, configuration.order_side)
        for configuration in configurations
    }


def test_central_forward_exposes_only_normal_and_defensive():
    assert _pairs(
        legal_orders_for_slot(Position.FORWARD, Side.CENTER, "2-5-3")
    ) == {
        (Order.NORMAL, None),
        (Order.DEFENSIVE, None),
    }


def test_central_forward_rejects_towards_wing():
    assert not is_legal_order_for_slot(
        Position.FORWARD,
        Side.CENTER,
        Order.TOWARDS_WING,
        Side.LEFT,
        "2-5-3",
    )


def test_side_forward_keeps_towards_wing_options():
    assert (Order.TOWARDS_WING, Side.LEFT) in _pairs(
        legal_orders_for_slot(Position.FORWARD, Side.LEFT, "2-5-3")
    )


def test_unknown_slot_falls_back_to_normal_goalkeeper_policy():
    assert normal_order_for_slot("NOT_A_POSITION").order == Order.NORMAL
