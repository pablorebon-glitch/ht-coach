from engine.calculators.contribution_calculator import (
    ContributionCalculator
)


class WingBack:

    def calculate(
        self,
        player,
        side=None
    ):

        return ContributionCalculator.calculate(
            player,
            "WING_BACK",
            side
        )