from dataclasses import dataclass

from engine.evaluators.match_evaluator import (
    MatchEvaluator
)

from engine.evaluators.result_probability_evaluator import (
    ResultProbabilityEvaluator
)

from engine.tactics.tactic_engine import (
    TacticEngine
)

from models.tactic import Tactic


@dataclass
class TacticOptimizationResult:

    tactic: Tactic

    tactic_level: float

    ratings: object

    match_evaluation: object

    probabilities: object

    tested_tactics: int

    baseline_win_probability: float


class TacticOptimizer:

    ALLOWED_TACTICS = tuple(
        Tactic
    )

    @staticmethod
    def _evaluate(
        base_ratings,
        tactic,
        opponent_ratings,
        lineup=None,
        config=None
    ):

        (
            context,
            effects
        ) = TacticEngine.evaluate_effects(
            lineup=lineup,
            base_ratings=base_ratings,
            opponent_ratings=opponent_ratings,
            tactic=tactic
        )

        match_evaluation = MatchEvaluator.evaluate(
            effects.ratings,
            opponent_ratings,
            our_distribution=(
                effects.our_distribution
            ),
            opponent_distribution=(
                effects.opponent_distribution
            ),
            our_chance_multiplier=(
                effects.our_chance_multiplier
            ),
            opponent_chance_multiplier=(
                effects.opponent_chance_multiplier
            ),
            counter_attack_chances=(
                effects.counter_attack_chances
            ),
            special_event_multiplier=(
                effects.special_event_multiplier
            ),
            long_shot_conversion_rate=(
                effects.long_shot_conversion_rate
            ),
            config=config
        )

        probabilities = (
            ResultProbabilityEvaluator.evaluate(
                match_evaluation.expected_goals,
                match_evaluation.opponent_expected_goals
            )
        )

        return (
            context,
            effects,
            match_evaluation,
            probabilities
        )

    @classmethod
    def optimize(
        cls,
        base_ratings,
        opponent_ratings,
        lineup=None,
        config=None
    ):

        baseline_probabilities = None

        best_tactic = Tactic.NORMAL
        best_tactic_level = 0.0

        best_ratings = None
        best_match_evaluation = None
        best_probabilities = None

        tested_tactics = 0

        for tactic in cls.ALLOWED_TACTICS:

            (
                context,
                effects,
                match_evaluation,
                probabilities
            ) = cls._evaluate(
                base_ratings,
                tactic,
                opponent_ratings,
                lineup=lineup,
                config=config
            )

            tested_tactics += 1

            if tactic == Tactic.NORMAL:

                baseline_probabilities = (
                    probabilities
                )

            if (
                best_probabilities is None
                or probabilities.win
                > best_probabilities.win
            ):

                best_tactic = tactic

                best_tactic_level = (
                    context.level
                )

                best_ratings = (
                    effects.ratings
                )

                best_match_evaluation = (
                    match_evaluation
                )

                best_probabilities = (
                    probabilities
                )

        return TacticOptimizationResult(
            tactic=best_tactic,
            tactic_level=best_tactic_level,
            ratings=best_ratings,
            match_evaluation=(
                best_match_evaluation
            ),
            probabilities=best_probabilities,
            tested_tactics=tested_tactics,
            baseline_win_probability=(
                baseline_probabilities.win
            )
        )