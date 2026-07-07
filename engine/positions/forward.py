from engine.calculators.contribution_calculator import (
    ContributionCalculator
)


class Forward:

    def calculate(
        self,
        player,
        side=None
    ):

        return ContributionCalculator.calculate(
            player,
            "FORWARD",
            side
        )