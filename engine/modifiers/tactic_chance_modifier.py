from models.chance_distribution import ChanceDistribution
from models.tactic import Tactic


class TacticChanceModifier:

    AIM_CENTER_FACTOR = 1.20
    AOW_WING_FACTOR = 1.20

    @staticmethod
    def _normalize(
        left,
        center,
        right
    ):

        total = left + center + right

        return ChanceDistribution(
            left=left / total,
            center=center / total,
            right=right / total
        )

    @classmethod
    def apply(
        cls,
        distribution,
        tactic
    ):

        if tactic == Tactic.NORMAL:

            return ChanceDistribution(
                left=distribution.left,
                center=distribution.center,
                right=distribution.right
            )

        left = distribution.left
        center = distribution.center
        right = distribution.right

        if tactic == Tactic.ATTACK_IN_MIDDLE:

            center *= cls.AIM_CENTER_FACTOR

        elif tactic == Tactic.ATTACK_ON_WINGS:

            left *= cls.AOW_WING_FACTOR
            right *= cls.AOW_WING_FACTOR

        return cls._normalize(
            left,
            center,
            right
        )