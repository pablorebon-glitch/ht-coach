from importers.csv_importer import load_players

from engine.optimizers.formation_optimizer import (
    FormationOptimizer
)

from models.formations import FORMATIONS

from models.team_ratings import TeamRatings

from reports.tactic_comparison_report import (
    TacticComparisonReport
)
from engine.analyzers.team_rater import (
    TeamRater
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

    results = (
        FormationOptimizer.optimize_against(
            players,
            FORMATIONS,
            opponent
        )
    )

    print()
    print("=" * 165)
    print("FORMATION MATCHUP ANALYSIS")
    print("=" * 165)

    print(
        f"{'FORMATION':<12}"
        f"{'TESTED XI':>12}"
        f"{'ORDER XI':>10}"
        f"{'ORDER CFG':>14}"
        f"{'TACTICS':>10}"
        f"{'BASE WIN':>12}"
        f"{'BEST NORMAL':>14}"
        f"{'BEST ORDER':>14}"
        f"{'BEST WIN':>12}"
        f"{'LINEUP GAIN':>14}"
        f"{'ORDER GAIN':>13}"
        f"{'TACTIC GAIN':>14}"
        f"{'POSSESSION':>14}"
        f"{'XG':>10}"
        f"{'OPP XG':>10}"
    )

    print("-" * 165)

    for result in results:

        lineup_gain = (
            result.best_normal_win_probability
            - result.baseline_win_probability
        )

        order_gain = (
            result.best_order_win_probability
            - result.best_normal_win_probability
        )

        tactic_gain = (
            result.probabilities.win
            - result.best_order_win_probability
        )

        print(
            f"{result.formation.name:<12}"
            f"{result.tested_lineups:>12}"
            f"{result.order_finalists:>10}"
            f"{result.tested_order_configurations:>14}"
            f"{result.tested_tactics:>10}"
            f"{result.baseline_win_probability * 100:>11.2f}%"
            f"{result.best_normal_win_probability * 100:>13.2f}%"
            f"{result.best_order_win_probability * 100:>13.2f}%"
            f"{result.probabilities.win * 100:>11.2f}%"
            f"{lineup_gain * 100:>13.2f}%"
            f"{order_gain * 100:>12.2f}%"
            f"{tactic_gain * 100:>13.2f}%"
            f"{result.match_evaluation.possession * 100:>13.2f}%"
            f"{result.match_evaluation.expected_goals:>10.2f}"
            f"{result.match_evaluation.opponent_expected_goals:>10.2f}"
        )

    print("=" * 165)

    best = results[0]

    print()
    print("=" * 100)
    print(
        "RECOMMENDED FORMATION AGAINST OPPONENT"
    )
    print("=" * 100)

    print(
        f"Formation       : "
        f"{best.formation.name}"
    )

    print()

    print("OPTIMIZATION")

    print(
        f"Baseline win    : "
        f"{best.baseline_win_probability * 100:.4f}%"
    )

    print(
        f"Best normal win : "
        f"{best.best_normal_win_probability * 100:.4f}%"
    )

    print(
        f"Best order win  : "
        f"{best.best_order_win_probability * 100:.4f}%"
    )

    print(
        f"Optimized win   : "
        f"{best.probabilities.win * 100:.4f}%"
    )

    lineup_improvement = (
        best.best_normal_win_probability
        - best.baseline_win_probability
    )

    order_improvement = (
        best.best_order_win_probability
        - best.best_normal_win_probability
    )

    tactic_improvement = (
        best.probabilities.win
        - best.best_order_win_probability
    )

    total_improvement = (
        best.probabilities.win
        - best.baseline_win_probability
    )

    print(
        f"Lineup gain     : "
        f"{lineup_improvement * 100:.4f}%"
    )

    print(
        f"Order gain      : "
        f"{order_improvement * 100:.4f}%"
    )

    print(
        f"Tactic gain     : "
        f"{tactic_improvement * 100:.4f}%"
    )

    print(
        f"Total gain      : "
        f"{total_improvement * 100:.4f}%"
    )

    print()

    print("TACTIC")

    print(
        f"Tactic          : "
        f"{best.tactic.value}"
    )

    print(
        f"Tactic level    : "
        f"{best.tactic_level:.2f}"
    )

    print()

    print("TEAM RATINGS")

    print(
        f"Left Defense    : "
        f"{best.ratings.left_defense:.2f}"
    )

    print(
        f"Central Defense : "
        f"{best.ratings.central_defense:.2f}"
    )

    print(
        f"Right Defense   : "
        f"{best.ratings.right_defense:.2f}"
    )

    print()

    print(
        f"Midfield        : "
        f"{best.ratings.midfield:.2f}"
    )

    print()

    print(
        f"Left Attack     : "
        f"{best.ratings.left_attack:.2f}"
    )

    print(
        f"Central Attack  : "
        f"{best.ratings.central_attack:.2f}"
    )

    print(
        f"Right Attack    : "
        f"{best.ratings.right_attack:.2f}"
    )

    print()

    print("MATCH EVALUATION")

    print(
        f"Possession      : "
        f"{best.match_evaluation.possession * 100:.2f}%"
    )

    print(
        f"Expected Chances: "
        f"{best.match_evaluation.expected_chances:.4f}"
    )

    print(
        f"Opponent Chances: "
        f"{best.match_evaluation.opponent_expected_chances:.4f}"
    )

    print(
        f"Expected Goals  : "
        f"{best.match_evaluation.expected_goals:.4f}"
    )

    print(
        f"Opponent XG     : "
        f"{best.match_evaluation.opponent_expected_goals:.4f}"
    )

    print()

    print("RESULT PROBABILITIES")

    print(
        f"Win             : "
        f"{best.probabilities.win * 100:.4f}%"
    )

    print(
        f"Draw            : "
        f"{best.probabilities.draw * 100:.4f}%"
    )

    print(
        f"Loss            : "
        f"{best.probabilities.loss * 100:.4f}%"
    )

    print()

    print("SEARCH")

    print(
        f"Candidate lineups tested     : "
        f"{best.tested_lineups}"
    )

    print(
        f"Order finalists optimized    : "
        f"{best.order_finalists}"
    )

    print(
        f"Order configurations tested  : "
        f"{best.tested_order_configurations}"
    )

    print(
        f"Tactics tested                : "
        f"{best.tested_tactics}"
    )

    print()

    print("BEST XI + ORDERS")

    for index, lineup_player in enumerate(
        best.lineup.players,
        start=1
    ):

        order_text = (
            lineup_player.order.value
        )

        if (
            lineup_player.order_side
            is not None
        ):

            order_text += (
                f" "
                f"({lineup_player.order_side.value})"
            )

        print(
            f"{index:>2}. "
            f"{lineup_player.side.value:8}"
            f"{lineup_player.position.value:22}"
            f"{order_text:28}"
            f"{lineup_player.player.name}"
        )

    # --------------------------------------------------
    # COMPARE ALL TACTICS USING THE WINNING LINEUP
    # --------------------------------------------------

    TacticComparisonReport.show(
        lineup=best.lineup,
        base_ratings=(
            TeamRater.calculate(
                best.lineup
            )
        ),
        opponent_ratings=opponent
    )


if __name__ == "__main__":
    main()