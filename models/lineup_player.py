from dataclasses import dataclass

from models.player import Player
from models.position import Position
from models.order import Order
from models.side import Side


@dataclass
class LineupPlayer:

    player: Player

    position: Position

    side: Side = Side.CENTER

    order: Order = Order.NORMAL

    order_side: Side | None = None