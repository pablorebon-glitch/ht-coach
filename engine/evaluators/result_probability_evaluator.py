import math
from dataclasses import dataclass


@dataclass
class ResultProbabilities:

    win: float
    draw: float
    loss: float


class ResultProbabilityEvaluator:

    MAX_GOALS = 12

    @staticmethod
    def _poisson_probability(goals, expected_goals):

        return (
            math.exp(-expected_goals)
            * expected_goals ** goals
            / math.factorial(goals)
        )

    @classmethod
    def evaluate(
        cls,
        expected_goals,
        opponent_expected_goals
    ):

        win_probability = 0.0
        draw_probability = 0.0
        loss_probability = 0.0

        for our_goals in range(cls.MAX_GOALS + 1):

            our_probability = cls._poisson_probability(
                our_goals,
                expected_goals
            )

            for opponent_goals in range(cls.MAX_GOALS + 1):

                opponent_probability = cls._poisson_probability(
                    opponent_goals,
                    opponent_expected_goals
                )

                result_probability = (
                    our_probability
                    * opponent_probability
                )

                if our_goals > opponent_goals:
                    win_probability += result_probability

                elif our_goals == opponent_goals:
                    draw_probability += result_probability

                else:
                    loss_probability += result_probability

        total_probability = (
            win_probability
            + draw_probability
            + loss_probability
        )

        if total_probability > 0:

            win_probability /= total_probability
            draw_probability /= total_probability
            loss_probability /= total_probability

        return ResultProbabilities(
            win=win_probability,
            draw=draw_probability,
            loss=loss_probability
        )