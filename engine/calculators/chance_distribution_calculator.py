from dataclasses import dataclass

from models.tactic import Tactic


@dataclass
class ChanceDistribution:

    left: float
    center: float
    right: float

    def total(self):

        return (
            self.left
            + self.center
            + self.right
        )


class ChanceDistributionCalculator:

    NORMAL_LEFT = 0.25
    NORMAL_CENTER = 0.50
    NORMAL_RIGHT = 0.25

    MAX_TACTIC_LEVEL = 20

    MAX_AIM_SHIFT = 0.10
    MAX_AOW_SHIFT = 0.10

    @classmethod
    def _normalize_tactic_level(
        cls,
        tactic_level
    ):

        if tactic_level is None:
            return 1.0

        tactic_level = max(
            0,
            min(
                tactic_level,
                cls.MAX_TACTIC_LEVEL
            )
        )

        return (
            tactic_level
            / cls.MAX_TACTIC_LEVEL
        )

    @classmethod
    def calculate(
        cls,
        tactic=Tactic.NORMAL,
        tactic_level=None
    ):

        if tactic == Tactic.NORMAL:

            return ChanceDistribution(
                left=cls.NORMAL_LEFT,
                center=cls.NORMAL_CENTER,
                right=cls.NORMAL_RIGHT
            )

        effectiveness = (
            cls._normalize_tactic_level(
                tactic_level
            )
        )

        if tactic == Tactic.ATTACK_IN_MIDDLE:

            shift = (
                cls.MAX_AIM_SHIFT
                * effectiveness
            )

            return ChanceDistribution(
                left=(
                    cls.NORMAL_LEFT
                    - shift / 2
                ),
                center=(
                    cls.NORMAL_CENTER
                    + shift
                ),
                right=(
                    cls.NORMAL_RIGHT
                    - shift / 2
                )
            )

        if tactic == Tactic.ATTACK_ON_WINGS:

            shift = (
                cls.MAX_AOW_SHIFT
                * effectiveness
            )

            return ChanceDistribution(
                left=(
                    cls.NORMAL_LEFT
                    + shift / 2
                ),
                center=(
                    cls.NORMAL_CENTER
                    - shift
                ),
                right=(
                    cls.NORMAL_RIGHT
                    + shift / 2
                )
            )

        return ChanceDistribution(
            left=cls.NORMAL_LEFT,
            center=cls.NORMAL_CENTER,
            right=cls.NORMAL_RIGHT
        )