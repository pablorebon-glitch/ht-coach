from importers.csv_importer import load_players

from engine.analyzers.team_rater import TeamRater

from engine.evaluators.match_evaluator import (
    MatchEvaluator
)

from engine.evaluators.result_probability_evaluator import (
    ResultProbabilityEvaluator
)

from engine.optimizers.lineup_optimizer import (
    LineupOptimizer
)

from engine.optimizers.order_optimizer import (
    OrderOptimizer
)

from models.formations import FORMATION_352
from models.team_ratings import TeamRatings


def evaluate_lineup(
    lineup,
    opponent
):

    ratings = TeamRater.calculate(
        lineup
    )

    match_evaluation = MatchEvaluator.evaluate(
        ratings,
        opponent
    )

    probabilities = (
        ResultProbabilityEvaluator.evaluate(
            match_evaluation.expected_goals,
            match_evaluation.opponent_expected_goals
        )
    )

    return (
        ratings,
        match_evaluation,
        probabilities
    )


def print_result(
    title,
    lineup,
    ratings,
    match_evaluation,
    probabilities
):

    print()
    print("=" * 110)
    print(title)
    print("=" * 110)

    print()
    print("TEAM RATINGS")

    print(
        f"Left Defense    : "
        f"{ratings.left_defense:.2f}"
    )

    print(
        f"Central Defense : "
        f"{ratings.central_defense:.2f}"
    )

    print(
        f"Right Defense   : "
        f"{ratings.right_defense:.2f}"
    )

    print()

    print(
        f"Midfield        : "
        f"{ratings.midfield:.2f}"
    )

    print()

    print(
        f"Left Attack     : "
        f"{ratings.left_attack:.2f}"
    )

    print(
        f"Central Attack  : "
        f"{ratings.central_attack:.2f}"
    )

    print(
        f"Right Attack    : "
        f"{ratings.right_attack:.2f}"
    )

    print()
    print("MATCH EVALUATION")

    print(
        f"Possession      : "
        f"{match_evaluation.possession * 100:.2f}%"
    )

    print(
        f"Expected Goals  : "
        f"{match_evaluation.expected_goals:.2f}"
    )

    print(
        f"Opponent XG     : "
        f"{match_evaluation.opponent_expected_goals:.2f}"
    )

    print()
    print("RESULT PROBABILITIES")

    print(
        f"Win             : "
        f"{probabilities.win * 100:.2f}%"
    )

    print(
        f"Draw            : "
        f"{probabilities.draw * 100:.2f}%"
    )

    print(
        f"Loss            : "
        f"{probabilities.loss * 100:.2f}%"
    )

    print()
    print("LINEUP")

    for lineup_player in lineup.players:

        print(
            f"{lineup_player.side.value:8}"
            f"{lineup_player.position.value:22}"
            f"{lineup_player.order.value:18}"
            f"{lineup_player.player.name}"
        )


def main():

    players = load_players(
        "players.csv"
    )

    opponent = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=24,
        midfield=40,
        left_attack=25,
        central_attack=30,
        right_attack=24
    )

    lineup = LineupOptimizer.optimize(
        players,
        FORMATION_352
    )

    (
        normal_ratings,
        normal_match_evaluation,
        normal_probabilities
    ) = evaluate_lineup(
        lineup,
        opponent
    )

    optimization = OrderOptimizer.optimize(
        lineup,
        opponent,
        beam_width=100
    )

    print_result(
        title="NORMAL ORDERS",
        lineup=lineup,
        ratings=normal_ratings,
        match_evaluation=normal_match_evaluation,
        probabilities=normal_probabilities
    )

    print_result(
        title="OPTIMIZED ORDERS",
        lineup=optimization.lineup,
        ratings=optimization.ratings,
        match_evaluation=(
            optimization.match_evaluation
        ),
        probabilities=optimization.probabilities
    )

    print()
    print("=" * 110)
    print("ORDER OPTIMIZATION SUMMARY")
    print("=" * 110)

    improvement = (
        optimization.probabilities.win
        - optimization.baseline_win_probability
    )

    print(
        f"Baseline win          : "
        f"{optimization.baseline_win_probability * 100:.2f}%"
    )

    print(
        f"Optimized win         : "
        f"{optimization.probabilities.win * 100:.2f}%"
    )

    print(
        f"Improvement           : "
        f"{improvement * 100:.2f}%"
    )

    print(
        f"Configurations tested : "
        f"{optimization.tested_configurations}"
    )


if __name__ == "__main__":
    main()