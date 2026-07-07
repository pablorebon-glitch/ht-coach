from models.contribution import Contribution
from models.order import Order
from models.position import Position
from models.side import Side


class OrderModifier:

    ORDER_FACTORS = {

        Position.CENTRAL_DEFENDER: {

            Order.OFFENSIVE: {
                "midfield": 1.40,
                "central_defense": 0.85,
                "left_defense": 0.85,
                "right_defense": 0.85,
            },

            Order.TOWARDS_WING: {
                "central_defense": 0.85,
                "lateral_defense": 1.25,
            },
        },

        Position.WING_BACK: {

            Order.OFFENSIVE: {
                "midfield": 1.15,
                "central_defense": 0.80,
                "lateral_defense": 0.75,
                "lateral_attack": 1.35,
            },

            Order.DEFENSIVE: {
                "midfield": 0.90,
                "central_defense": 1.20,
                "lateral_defense": 1.25,
                "lateral_attack": 0.65,
            },

            Order.TOWARDS_MIDDLE: {
                "midfield": 1.20,
                "central_defense": 1.20,
                "lateral_defense": 0.80,
                "lateral_attack": 0.75,
            },
        },

        Position.INNER_MIDFIELDER: {

            Order.OFFENSIVE: {
                "midfield": 0.95,
                "central_defense": 0.75,
                "left_defense": 0.75,
                "right_defense": 0.75,
                "central_attack": 1.25,
                "left_attack": 1.15,
                "right_attack": 1.15,
            },

            Order.DEFENSIVE: {
                "midfield": 0.95,
                "central_defense": 1.30,
                "left_defense": 1.30,
                "right_defense": 1.30,
                "central_attack": 0.75,
                "left_attack": 0.75,
                "right_attack": 0.75,
            },

            Order.TOWARDS_WING: {
                "midfield": 0.90,
                "central_defense": 0.90,
                "central_attack": 0.85,
                "lateral_attack": 1.35,
            },
        },

        Position.WINGER: {

            Order.OFFENSIVE: {
                "midfield": 0.85,
                "central_defense": 0.75,
                "lateral_defense": 0.75,
                "central_attack": 1.15,
                "lateral_attack": 1.25,
            },

            Order.DEFENSIVE: {
                "midfield": 0.90,
                "central_defense": 1.30,
                "lateral_defense": 1.35,
                "central_attack": 0.80,
                "lateral_attack": 0.75,
            },

            Order.TOWARDS_MIDDLE: {
                "midfield": 1.35,
                "central_defense": 1.15,
                "lateral_defense": 0.80,
                "central_attack": 1.20,
                "lateral_attack": 0.65,
            },
        },

        Position.FORWARD: {

            Order.DEFENSIVE: {
                "midfield": 1.35,
                "central_attack": 0.80,
                "left_attack": 0.80,
                "right_attack": 0.80,
            },

            Order.TOWARDS_WING: {
                "central_attack": 0.75,
                "lateral_attack": 1.40,
            },
        },
    }

    @staticmethod
    def _resolve_area(
        area,
        side,
        order_side=None
    ):

        effective_side = (
            order_side
            if order_side is not None
            else side
        )

        if area == "lateral_defense":

            if effective_side == Side.LEFT:
                return "left_defense"

            if effective_side == Side.RIGHT:
                return "right_defense"

            return None

        if area == "lateral_attack":

            if effective_side == Side.LEFT:
                return "left_attack"

            if effective_side == Side.RIGHT:
                return "right_attack"

            return None

        return area

    @classmethod
    def apply(
        cls,
        contribution,
        position,
        side,
        order,
        order_side=None
    ):

        if order == Order.NORMAL:
            return contribution

        position_config = cls.ORDER_FACTORS.get(
            position,
            {}
        )

        factors = position_config.get(
            order
        )

        if factors is None:
            return contribution

        values = {
            "left_defense": contribution.left_defense,
            "central_defense": contribution.central_defense,
            "right_defense": contribution.right_defense,
            "midfield": contribution.midfield,
            "left_attack": contribution.left_attack,
            "central_attack": contribution.central_attack,
            "right_attack": contribution.right_attack,
        }

        for area, factor in factors.items():

            resolved_area = cls._resolve_area(
                area,
                side,
                order_side
            )

            if resolved_area is None:
                continue

            values[resolved_area] *= factor

        return Contribution(
            left_defense=round(
                values["left_defense"],
                2
            ),
            central_defense=round(
                values["central_defense"],
                2
            ),
            right_defense=round(
                values["right_defense"],
                2
            ),
            midfield=round(
                values["midfield"],
                2
            ),
            left_attack=round(
                values["left_attack"],
                2
            ),
            central_attack=round(
                values["central_attack"],
                2
            ),
            right_attack=round(
                values["right_attack"],
                2
            )
        )