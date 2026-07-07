from engine.calculators.advanced_tactic_level_calculator import (
    AdvancedTacticLevelCalculator
)

from engine.calculators.chance_distribution_calculator import (
    ChanceDistributionCalculator
)

from engine.evaluators.match_evaluator import (
    MatchEvaluator
)

from engine.modifiers.tactic_modifier import (
    TacticModifier
)

from engine.tactics.tactic_context import (
    TacticContext
)

from engine.tactics.tactic_effects import (
    TacticEffects
)

from models.tactic import Tactic


class TacticEngine:

    PRESSING_MAX_REDUCTION = 0.30

    COUNTER_ATTACK_MAX_CHANCES = 2.00

    PLAY_CREATIVELY_ACTIVATION_LEVEL = 12.0

    PLAY_CREATIVELY_MAX_EVENT_BONUS = 0.50

    PLAY_CREATIVELY_MAX_DEFENSIVE_PENALTY = 0.10

    LONG_SHOTS_MAX_CONVERSION_RATE = 0.35

    LONG_SHOTS_ACTIVATION_THRESHOLD = 0.35

    @classmethod
    def _calculate_level(
        cls,
        lineup,
        tactic
    ):

        return (
            AdvancedTacticLevelCalculator.calculate(
                lineup,
                tactic
            )
        )

    @staticmethod
    def _level_ratio(
        level
    ):

        return max(
            0.0,
            min(
                1.0,
                level / 20.0
            )
        )

    @staticmethod
    def _possession_share(
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

    @classmethod
    def _counter_attack_chances(
        cls,
        level_ratio,
        midfield,
        opponent_midfield
    ):

        possession = cls._possession_share(
            midfield,
            opponent_midfield
        )

        if possession >= 0.5:
            return 0.0

        opponent_dominance = (
            0.5 - possession
        ) / 0.5

        return (
            cls.COUNTER_ATTACK_MAX_CHANCES
            * level_ratio
            * opponent_dominance
        )

    @staticmethod
    def _average_normal_conversion(
        ratings,
        opponent_ratings
    ):

        left_conversion = (
            MatchEvaluator._goal_probability(
                ratings.left_attack,
                opponent_ratings.right_defense
            )
        )

        central_conversion = (
            MatchEvaluator._goal_probability(
                ratings.central_attack,
                opponent_ratings.central_defense
            )
        )

        right_conversion = (
            MatchEvaluator._goal_probability(
                ratings.right_attack,
                opponent_ratings.left_defense
            )
        )

        return (
            left_conversion
            + central_conversion
            + right_conversion
        ) / 3.0

    @classmethod
    def build_context(
        cls,
        lineup,
        base_ratings,
        opponent_ratings,
        tactic
    ):

        level = cls._calculate_level(
            lineup,
            tactic
        )

        return TacticContext(
            tactic=tactic,
            level=level,
            lineup=lineup,
            base_ratings=base_ratings,
            opponent_ratings=opponent_ratings
        )

    @classmethod
    def apply(
        cls,
        context
    ):

        tactic = context.tactic

        level_ratio = cls._level_ratio(
            context.level
        )

        ratings = TacticModifier.apply(
            context.base_ratings,
            tactic
        )

        our_distribution = (
            ChanceDistributionCalculator.calculate(
                tactic,
                tactic_level=context.level
            )
        )

        opponent_distribution = (
            ChanceDistributionCalculator.calculate(
                Tactic.NORMAL
            )
        )

        effects = TacticEffects(
            ratings=ratings,
            our_distribution=our_distribution,
            opponent_distribution=opponent_distribution
        )

        # --------------------------------------------------
        # PRESSING
        # --------------------------------------------------

        if tactic == Tactic.PRESSING:

            reduction = (
                cls.PRESSING_MAX_REDUCTION
                * level_ratio
            )

            effects.our_chance_multiplier = (
                1.0 - reduction
            )

            effects.opponent_chance_multiplier = (
                1.0 - reduction
            )

        # --------------------------------------------------
        # COUNTER ATTACKS
        # --------------------------------------------------

        elif tactic == Tactic.COUNTER_ATTACKS:

            effects.counter_attack_chances = (
                cls._counter_attack_chances(
                    level_ratio=level_ratio,
                    midfield=(
                        context.base_ratings.midfield
                    ),
                    opponent_midfield=(
                        context.opponent_ratings.midfield
                    )
                )
            )

        # --------------------------------------------------
        # PLAY CREATIVELY
        # --------------------------------------------------

        elif tactic == Tactic.PLAY_CREATIVELY:

            if (
                context.level
                < cls.PLAY_CREATIVELY_ACTIVATION_LEVEL
            ):

                effects.special_event_multiplier = 1.0

            else:

                activation_range = (
                    20.0
                    - cls.PLAY_CREATIVELY_ACTIVATION_LEVEL
                )

                effective_level = (
                    context.level
                    - cls.PLAY_CREATIVELY_ACTIVATION_LEVEL
                )

                activation_ratio = (
                    effective_level
                    / activation_range
                )

                activation_ratio = max(
                    0.0,
                    min(
                        1.0,
                        activation_ratio
                    )
                )

                effects.special_event_multiplier = (
                    1.0
                    + (
                        cls.PLAY_CREATIVELY_MAX_EVENT_BONUS
                        * activation_ratio
                    )
                )

                defensive_penalty = (
                    cls.PLAY_CREATIVELY_MAX_DEFENSIVE_PENALTY
                    * activation_ratio
                )

                effects.ratings.left_defense *= (
                    1.0
                    - defensive_penalty
                )

                effects.ratings.central_defense *= (
                    1.0
                    - defensive_penalty
                )

                effects.ratings.right_defense *= (
                    1.0
                    - defensive_penalty
                )

        # --------------------------------------------------
        # LONG SHOTS
        # --------------------------------------------------

        elif tactic == Tactic.LONG_SHOTS:

            normal_conversion = (
                cls._average_normal_conversion(
                    ratings,
                    context.opponent_ratings
                )
            )

            if (
                normal_conversion
                >= cls.LONG_SHOTS_ACTIVATION_THRESHOLD
            ):

                effects.long_shot_conversion_rate = 0.0

            else:

                defensive_resistance = (
                    cls.LONG_SHOTS_ACTIVATION_THRESHOLD
                    - normal_conversion
                ) / cls.LONG_SHOTS_ACTIVATION_THRESHOLD

                effects.long_shot_conversion_rate = (
                    cls.LONG_SHOTS_MAX_CONVERSION_RATE
                    * level_ratio
                    * defensive_resistance
                )

        return effects

    @classmethod
    def evaluate_effects(
        cls,
        lineup,
        base_ratings,
        opponent_ratings,
        tactic
    ):

        context = cls.build_context(
            lineup=lineup,
            base_ratings=base_ratings,
            opponent_ratings=opponent_ratings,
            tactic=tactic
        )

        effects = cls.apply(
            context
        )

        return (
            context,
            effects
        )