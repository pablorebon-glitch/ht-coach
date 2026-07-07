from models.side import Side

from engine.calculators.contribution_calculator import (
    ContributionCalculator
)

from engine.config.coefficients import POSITION_COEFFICIENTS


class PlayerRatingEngine:

    @staticmethod
    def calculate(
        player,
        position,
        side=Side.CENTER
    ):

        if position not in POSITION_COEFFICIENTS:
            return 0

        contribution = ContributionCalculator.calculate(
            player,
            position,
            side
        )

        score = (
            contribution.left_defense
            + contribution.central_defense
            + contribution.right_defense
            + contribution.midfield
            + contribution.left_attack
            + contribution.central_attack
            + contribution.right_attack
        )

        return round(
            score,
            2
        )

    @staticmethod
    def best_position(player):

        best_position = None
        best_score = -1

        for position in POSITION_COEFFICIENTS:

            score = PlayerRatingEngine.calculate(
                player,
                position
            )

            if score > best_score:

                best_score = score
                best_position = position

        return (
            best_position,
            best_score
        )