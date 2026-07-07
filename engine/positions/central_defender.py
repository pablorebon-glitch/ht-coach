from engine.calculators.contribution_calculator import (
    ContributionCalculator
)


class CentralDefender:

    def calculate(
        self,
        player,
        side=None
    ):

        return ContributionCalculator.calculate(
            player,
            "CENTRAL_DEFENDER",
            side
        )