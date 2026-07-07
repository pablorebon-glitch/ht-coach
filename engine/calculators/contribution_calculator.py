from models.contribution import Contribution
from models.side import Side

from engine.config.coefficients import POSITION_COEFFICIENTS

from engine.performance.player_performance import (
    PlayerPerformance
)


class ContributionCalculator:

    @staticmethod
    def _is_lateral_area(area):

        return area in {
            "left_defense",
            "right_defense",
            "left_attack",
            "right_attack",
        }

    @staticmethod
    def _should_apply_area(
        area,
        side
    ):

        if not ContributionCalculator._is_lateral_area(
            area
        ):
            return True

        if side == Side.LEFT:

            return area in {
                "left_defense",
                "left_attack",
            }

        if side == Side.RIGHT:

            return area in {
                "right_defense",
                "right_attack",
            }

        return True

    @classmethod
    def calculate(
        cls,
        player,
        position,
        side=Side.CENTER
    ):

        contribution = Contribution()

        config = POSITION_COEFFICIENTS[
            position
        ]

        for area, skills in config.items():

            if not cls._should_apply_area(
                area,
                side
            ):
                continue

            total = 0

            for skill, coefficient in skills.items():

                effective_value = (
                    PlayerPerformance.effective_skill(
                        player,
                        skill
                    )
                )

                total += (
                    effective_value
                    * coefficient
                )

            setattr(
                contribution,
                area,
                round(
                    total,
                    2
                )
            )

        return contribution