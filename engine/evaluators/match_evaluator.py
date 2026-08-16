from dataclasses import dataclass

from engine.calculators.chance_distribution_calculator import (
    ChanceDistributionCalculator
)

from models.match_model_config import (
    MatchModelConfig
)

from models.tactic import Tactic

from models.rating_scale import RatingScale

from engine.ratings.rating_scale_normalizer import (
    rating_scale_of,
    validate_compatible_ratings,
)


@dataclass
class MatchEvaluation:

    possession: float

    chance_probability: float
    opponent_chance_probability: float

    expected_chances: float
    opponent_expected_chances: float

    left_conversion: float
    central_conversion: float
    right_conversion: float

    opponent_left_conversion: float
    opponent_central_conversion: float
    opponent_right_conversion: float

    expected_goals: float
    opponent_expected_goals: float


class MatchEvaluator:

    DEFAULT_CONFIG = MatchModelConfig()

    @staticmethod
    def _resolve_config(
        config=None
    ):

        if config is None:
            return MatchEvaluator.DEFAULT_CONFIG

        return config

    @staticmethod
    def _possession_share(
        midfield,
        opponent_midfield
    ):

        total = midfield + opponent_midfield

        if total <= 0:
            return 0.5

        return midfield / total

    @classmethod
    def _chance_probability(
        cls,
        midfield,
        opponent_midfield,
        config=None
    ):

        config = cls._resolve_config(
            config
        )

        exponent = (
            config.midfield_chance_share_exponent
        )

        our_strength = (
            midfield ** exponent
        )

        opponent_strength = (
            opponent_midfield ** exponent
        )

        total = (
            our_strength
            + opponent_strength
        )

        if total <= 0:
            return 0.5

        return (
            our_strength
            / total
        )

    @classmethod
    def _goal_probability(
        cls,
        attack,
        defense,
        config=None
    ):

        config = cls._resolve_config(
            config
        )

        attack_strength = (
            config.goal_conversion_factor
            * attack ** 3
        )

        defense_strength = (
            defense ** 3
        )

        total = (
            attack_strength
            + defense_strength
        )

        if total <= 0:
            return 0.5

        return (
            attack_strength
            / total
        )

    @classmethod
    def _expected_normal_chances(
        cls,
        chance_probability,
        config=None
    ):

        config = cls._resolve_config(
            config
        )

        return (
            config.exclusive_chances_per_team
            * chance_probability

            + config.shared_chances
            * chance_probability
        )

    @staticmethod
    def _expected_goals(
        expected_chances,
        left_conversion,
        central_conversion,
        right_conversion,
        distribution
    ):

        return (
            expected_chances
            * distribution.left
            * left_conversion

            + expected_chances
            * distribution.center
            * central_conversion

            + expected_chances
            * distribution.right
            * right_conversion
        )

    @staticmethod
    def _average_conversion(
        left_conversion,
        central_conversion,
        right_conversion
    ):

        return (
            left_conversion
            + central_conversion
            + right_conversion
        ) / 3.0

    @classmethod
    def evaluate(
        cls,
        our_ratings,
        opponent_ratings,
        tactic=Tactic.NORMAL,
        our_distribution=None,
        opponent_distribution=None,
        our_chance_multiplier=1.0,
        opponent_chance_multiplier=1.0,
        counter_attack_chances=0.0,
        special_event_multiplier=1.0,
        long_shot_conversion_rate=0.0,
        config=None
    ):

        config = cls._resolve_config(
            config
        )

        cls._validate_rating_scales(
            our_ratings,
            opponent_ratings
        )

        possession = cls._possession_share(
            our_ratings.midfield,
            opponent_ratings.midfield
        )

        chance_probability = (
            cls._chance_probability(
                our_ratings.midfield,
                opponent_ratings.midfield,
                config
            )
        )

        opponent_chance_probability = (
            1.0 - chance_probability
        )

        expected_chances = (
            cls._expected_normal_chances(
                chance_probability,
                config
            )
            * our_chance_multiplier
        )

        opponent_expected_chances = (
            cls._expected_normal_chances(
                opponent_chance_probability,
                config
            )
            * opponent_chance_multiplier
        )

        left_conversion = cls._goal_probability(
            our_ratings.left_attack,
            opponent_ratings.right_defense,
            config
        )

        central_conversion = cls._goal_probability(
            our_ratings.central_attack,
            opponent_ratings.central_defense,
            config
        )

        right_conversion = cls._goal_probability(
            our_ratings.right_attack,
            opponent_ratings.left_defense,
            config
        )

        opponent_left_conversion = (
            cls._goal_probability(
                opponent_ratings.left_attack,
                our_ratings.right_defense,
                config
            )
        )

        opponent_central_conversion = (
            cls._goal_probability(
                opponent_ratings.central_attack,
                our_ratings.central_defense,
                config
            )
        )

        opponent_right_conversion = (
            cls._goal_probability(
                opponent_ratings.right_attack,
                our_ratings.left_defense,
                config
            )
        )

        if our_distribution is None:

            our_distribution = (
                ChanceDistributionCalculator.calculate(
                    tactic
                )
            )

        if opponent_distribution is None:

            opponent_distribution = (
                ChanceDistributionCalculator.calculate(
                    Tactic.NORMAL
                )
            )

        expected_goals = cls._expected_goals(
            expected_chances,
            left_conversion,
            central_conversion,
            right_conversion,
            our_distribution
        )

        opponent_expected_goals = (
            cls._expected_goals(
                opponent_expected_chances,
                opponent_left_conversion,
                opponent_central_conversion,
                opponent_right_conversion,
                opponent_distribution
            )
        )

        average_conversion = (
            cls._average_conversion(
                left_conversion,
                central_conversion,
                right_conversion
            )
        )

        # --------------------------------------------------
        # COUNTER ATTACKS
        # --------------------------------------------------

        if counter_attack_chances > 0:

            expected_chances += (
                counter_attack_chances
            )

            expected_goals += (
                counter_attack_chances
                * average_conversion
            )

        # --------------------------------------------------
        # PLAY CREATIVELY
        # --------------------------------------------------

        if special_event_multiplier > 1.0:

            special_event_bonus = (
                special_event_multiplier
                - 1.0
            )

            special_event_chances = (
                config.special_event_base_chances
                * special_event_bonus
            )

            special_event_conversion = (
                average_conversion
                * config.special_event_goal_factor
            )

            expected_chances += (
                special_event_chances
            )

            expected_goals += (
                special_event_chances
                * special_event_conversion
            )

        # --------------------------------------------------
        # LONG SHOTS
        # --------------------------------------------------

        if long_shot_conversion_rate > 0:

            converted_chances = (
                expected_chances
                * long_shot_conversion_rate
            )

            normal_goal_rate = (
                expected_goals
                / expected_chances
                if expected_chances > 0
                else 0.0
            )

            expected_goals -= (
                converted_chances
                * normal_goal_rate
            )

            expected_goals += (
                converted_chances
                * config.long_shot_goal_factor
                * average(
                    (
                        our_ratings.scoring
                        if hasattr(
                            our_ratings,
                            "scoring"
                        )
                        else our_ratings.central_attack
                    ),
                    our_ratings.central_attack
                )
                / (
                    average(
                        our_ratings.central_attack,
                        opponent_ratings.central_defense
                    )
                    + 1.0
                )
            )

        return MatchEvaluation(
            possession=possession,

            chance_probability=chance_probability,

            opponent_chance_probability=(
                opponent_chance_probability
            ),

            expected_chances=expected_chances,

            opponent_expected_chances=(
                opponent_expected_chances
            ),

            left_conversion=left_conversion,
            central_conversion=central_conversion,
            right_conversion=right_conversion,

            opponent_left_conversion=(
                opponent_left_conversion
            ),

            opponent_central_conversion=(
                opponent_central_conversion
            ),

            opponent_right_conversion=(
                opponent_right_conversion
            ),

            expected_goals=expected_goals,

            opponent_expected_goals=(
                opponent_expected_goals
            )
        )

    @staticmethod
    def _validate_rating_scales(
        our_ratings,
        opponent_ratings
    ):
        our_scale = rating_scale_of(
            our_ratings
        )
        opponent_scale = rating_scale_of(
            opponent_ratings
        )

        if (
            our_scale == RatingScale.UNKNOWN
            and opponent_scale == RatingScale.UNKNOWN
        ):
            return True

        return validate_compatible_ratings(
            our_ratings,
            opponent_ratings
        )


def average(
    first,
    second
):

    return (
        first
        + second
    ) / 2.0
