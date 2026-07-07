from dataclasses import dataclass

from engine.config.match_model_config import (
    DEFAULT_MATCH_MODEL_CONFIG
)


@dataclass(frozen=True)
class NormalChanceResult:

    possession: float

    chance_probability: float
    opponent_chance_probability: float

    expected_chances: float
    opponent_expected_chances: float


class NormalChanceCalculator:

    @staticmethod
    def possession_share(
        midfield,
        opponent_midfield
    ):

        total = (
            midfield
            + opponent_midfield
        )

        if total <= 0:
            return 0.5

        return (
            midfield
            / total
        )

    @staticmethod
    def chance_share_from_possession(
        possession,
        config=DEFAULT_MATCH_MODEL_CONFIG
    ):

        possession = max(
            0.0,
            min(
                1.0,
                possession
            )
        )

        opponent_possession = (
            1.0
            - possession
        )

        our_strength = (
            possession
            ** config.midfield_chance_share_exponent
        )

        opponent_strength = (
            opponent_possession
            ** config.midfield_chance_share_exponent
        )

        total_strength = (
            our_strength
            + opponent_strength
        )

        if total_strength <= 0:
            return 0.5

        return (
            our_strength
            / total_strength
        )

    @staticmethod
    def expected_normal_chances(
        chance_probability,
        config=DEFAULT_MATCH_MODEL_CONFIG
    ):

        return (
            config.normal_chances_per_match
            * chance_probability
        )

    @classmethod
    def chance_probability(
        cls,
        midfield,
        opponent_midfield,
        config=DEFAULT_MATCH_MODEL_CONFIG
    ):

        possession = (
            cls.possession_share(
                midfield,
                opponent_midfield
            )
        )

        return (
            cls.chance_share_from_possession(
                possession,
                config=config
            )
        )

    @classmethod
    def calculate(
        cls,
        midfield,
        opponent_midfield,
        config=DEFAULT_MATCH_MODEL_CONFIG
    ):

        possession = (
            cls.possession_share(
                midfield,
                opponent_midfield
            )
        )

        chance_probability = (
            cls.chance_share_from_possession(
                possession,
                config=config
            )
        )

        opponent_chance_probability = (
            1.0
            - chance_probability
        )

        expected_chances = (
            cls.expected_normal_chances(
                chance_probability,
                config=config
            )
        )

        opponent_expected_chances = (
            cls.expected_normal_chances(
                opponent_chance_probability,
                config=config
            )
        )

        return NormalChanceResult(
            possession=possession,

            chance_probability=(
                chance_probability
            ),

            opponent_chance_probability=(
                opponent_chance_probability
            ),

            expected_chances=(
                expected_chances
            ),

            opponent_expected_chances=(
                opponent_expected_chances
            )
        )