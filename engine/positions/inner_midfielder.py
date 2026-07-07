from engine.calculators.contribution_calculator import (
    ContributionCalculator
)


class InnerMidfielder:

    def calculate(
        self,
        player,
        side=None
    ):

        return ContributionCalculator.calculate(
            player,
            "INNER_MIDFIELDER",
            side
        )