from engine.calculators.contribution_calculator import (
    ContributionCalculator
)


class Winger:

    def calculate(
        self,
        player,
        side=None
    ):

        return ContributionCalculator.calculate(
            player,
            "WINGER",
            side
        )