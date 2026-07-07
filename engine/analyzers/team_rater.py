from engine.position_registry import POSITION_ENGINES

from engine.calculators.team_calculator import (
    TeamCalculator
)

from engine.orders.order_modifier import (
    OrderModifier
)


class TeamRater:

    @staticmethod
    def calculate(lineup):

        contributions = []

        for lineup_player in lineup.players:

            engine = POSITION_ENGINES[
                lineup_player.position.value
            ]

            contribution = engine.calculate(
                lineup_player.player,
                lineup_player.side
            )

            contribution = OrderModifier.apply(
                contribution=contribution,
                position=lineup_player.position,
                side=lineup_player.side,
                order=lineup_player.order,
                order_side=lineup_player.order_side
            )

            contributions.append(
                contribution
            )

        calculator = TeamCalculator()

        return calculator.calculate(
            contributions
        )