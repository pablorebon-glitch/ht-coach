from engine.calculators.contribution_calculator import (
    ContributionCalculator
)


class Goalkeeper:

    def calculate(
        self,
        player,
        side=None
    ):

        return ContributionCalculator.calculate(
            player,
            "GOALKEEPER",
            side
        )