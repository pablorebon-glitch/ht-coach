from copy import deepcopy
from dataclasses import dataclass

from engine.analyzers.team_rater import TeamRater
from engine.orders.legal_orders import OrderConfiguration
from engine.orders.legal_orders import base_allowed_configurations
from engine.orders.legal_orders import legal_orders_for_slot

from engine.evaluators.match_evaluator import (
    MatchEvaluator
)

from engine.evaluators.result_probability_evaluator import (
    ResultProbabilityEvaluator
)

from engine.ratings.rating_scale_normalizer import RatingScaleNormalizer

from models.order import Order
from models.position import Position


DEFAULT_RATING_NORMALIZER = RatingScaleNormalizer()


@dataclass
class OrderOptimizationResult:

    lineup: object

    ratings: object

    match_evaluation: object

    probabilities: object

    tested_configurations: int

    baseline_win_probability: float


@dataclass
class PartialOrderConfiguration:

    lineup: object

    next_player_index: int

    probabilities: object


class OrderOptimizer:

    DEFAULT_BEAM_WIDTH = 100

    ALLOWED_CONFIGURATIONS = base_allowed_configurations()

    @staticmethod
    def _evaluate_lineup(
        lineup,
        opponent_ratings,
        config=None
    ):

        ratings = TeamRater.calculate(
            lineup
        )

        (
            calibrated,
            opponent_calibrated
        ) = DEFAULT_RATING_NORMALIZER.normalize_matchup(
            ratings,
            opponent_ratings
        )

        if config is None:

            match_evaluation = (
                MatchEvaluator.evaluate(
                    calibrated.ratings,
                    opponent_calibrated
                )
            )

        else:

            match_evaluation = (
                MatchEvaluator.evaluate(
                    calibrated.ratings,
                    opponent_calibrated,
                    config=config
                )
            )

        probabilities = (
            ResultProbabilityEvaluator.evaluate(
                match_evaluation.expected_goals,
                match_evaluation.opponent_expected_goals
            )
        )

        return (
            calibrated.ratings,
            match_evaluation,
            probabilities
        )

    @classmethod
    def optimize(
        cls,
        lineup,
        opponent_ratings,
        beam_width=None,
        config=None
    ):

        if beam_width is None:

            beam_width = (
                cls.DEFAULT_BEAM_WIDTH
            )

        baseline_lineup = deepcopy(
            lineup
        )

        for lineup_player in baseline_lineup.players:

            lineup_player.order = Order.NORMAL

            lineup_player.order_side = None

        (
            baseline_ratings,
            baseline_match_evaluation,
            baseline_probabilities
        ) = cls._evaluate_lineup(
            baseline_lineup,
            opponent_ratings,
            config=config
        )

        beam = [
            PartialOrderConfiguration(
                lineup=baseline_lineup,
                next_player_index=0,
                probabilities=baseline_probabilities
            )
        ]

        tested_configurations = 0

        player_count = len(
            baseline_lineup.players
        )

        for player_index in range(
            player_count
        ):

            next_beam = []

            for partial in beam:

                lineup_player = (
                    partial.lineup.players[
                        player_index
                    ]
                )

                configurations = legal_orders_for_slot(
                    lineup_player.position,
                    lineup_player.side,
                    tactical_context=config,
                )

                for configuration in configurations:

                    candidate_lineup = deepcopy(
                        partial.lineup
                    )

                    candidate_player = (
                        candidate_lineup.players[
                            player_index
                        ]
                    )

                    candidate_player.order = (
                        configuration.order
                    )

                    candidate_player.order_side = (
                        configuration.order_side
                    )

                    (
                        _,
                        _,
                        probabilities
                    ) = cls._evaluate_lineup(
                        candidate_lineup,
                        opponent_ratings,
                        config=config
                    )

                    tested_configurations += 1

                    next_beam.append(
                        PartialOrderConfiguration(
                            lineup=candidate_lineup,
                            next_player_index=(
                                player_index + 1
                            ),
                            probabilities=probabilities
                        )
                    )

            next_beam.sort(
                key=lambda partial: (
                    partial.probabilities.win
                ),
                reverse=True
            )

            beam = next_beam[
                :beam_width
            ]

            if not beam:

                break

        best_lineup = baseline_lineup

        best_ratings = baseline_ratings

        best_match_evaluation = (
            baseline_match_evaluation
        )

        best_probabilities = (
            baseline_probabilities
        )

        for partial in beam:

            (
                ratings,
                match_evaluation,
                probabilities
            ) = cls._evaluate_lineup(
                partial.lineup,
                opponent_ratings,
                config=config
            )

            if (
                probabilities.win
                > best_probabilities.win
            ):

                best_lineup = partial.lineup

                best_ratings = ratings

                best_match_evaluation = (
                    match_evaluation
                )

                best_probabilities = (
                    probabilities
                )

        return OrderOptimizationResult(
            lineup=best_lineup,
            ratings=best_ratings,
            match_evaluation=(
                best_match_evaluation
            ),
            probabilities=best_probabilities,
            tested_configurations=(
                tested_configurations
            ),
            baseline_win_probability=(
                baseline_probabilities.win
            )
        )
