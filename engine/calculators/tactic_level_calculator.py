from engine.performance.player_performance import (
    PlayerPerformance
)

from models.position import Position
from models.tactic import Tactic


class TacticLevelCalculator:

    MIN_LEVEL = 0.0
    MAX_LEVEL = 20.0

    @classmethod
    def _clamp(
        cls,
        value
    ):

        return max(
            cls.MIN_LEVEL,
            min(
                value,
                cls.MAX_LEVEL
            )
        )

    @classmethod
    def calculate(
        cls,
        lineup,
        tactic
    ):

        if tactic == Tactic.NORMAL:
            return 0.0

        passing_values = []

        for lineup_player in lineup.players:

            if (
                lineup_player.position
                == Position.GOALKEEPER
            ):
                continue

            effective_passing = (
                PlayerPerformance.effective_skill(
                    lineup_player.player,
                    "passing"
                )
            )

            passing_values.append(
                effective_passing
            )

        if not passing_values:
            return 0.0

        average_passing = (
            sum(passing_values)
            / len(passing_values)
        )

        return round(
            cls._clamp(
                average_passing
            ),
            2
        )