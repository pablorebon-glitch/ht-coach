from engine.optimizers.tactic_optimizer import (
    TacticOptimizer
)
from engine.analyzers.team_rater import (
    TeamRater
)

class TacticComparisonReport:

    @staticmethod
    def show(
        lineup,
        base_ratings,
        opponent_ratings
    ):

        print()
        print("=" * 170)
        print("TACTIC COMPARISON")
        print("=" * 170)

        print(
            f"{'TACTIC':<24}"
            f"{'LEVEL':>10}"
            f"{'WIN':>12}"
            f"{'DRAW':>12}"
            f"{'LOSS':>12}"
            f"{'XG':>12}"
            f"{'OPP XG':>12}"
            f"{'CHANCES':>12}"
            f"{'OPP CH':>12}"
            f"{'CH MULT':>12}"
            f"{'OPP MULT':>12}"
            f"{'COUNTERS':>12}"
            f"{'CREATIVE':>12}"
            f"{'LONG SHOT':>12}"
        )

        print("-" * 170)

        rows = []

        for tactic in TacticOptimizer.ALLOWED_TACTICS:

            (
                context,
                effects,
                match_evaluation,
                probabilities
            ) = TacticOptimizer._evaluate(
                base_ratings,
                tactic,
                opponent_ratings,
                lineup=lineup
            )

            rows.append(
                (
                    tactic,
                    context,
                    effects,
                    match_evaluation,
                    probabilities
                )
            )

        rows.sort(
            key=lambda row: (
                row[4].win
            ),
            reverse=True
        )

        for (
            tactic,
            context,
            effects,
            match_evaluation,
            probabilities
        ) in rows:

            print(
                f"{tactic.value:<24}"
                f"{context.level:>10.2f}"
                f"{probabilities.win * 100:>11.4f}%"
                f"{probabilities.draw * 100:>11.4f}%"
                f"{probabilities.loss * 100:>11.4f}%"
                f"{match_evaluation.expected_goals:>12.4f}"
                f"{match_evaluation.opponent_expected_goals:>12.4f}"
                f"{match_evaluation.expected_chances:>12.4f}"
                f"{match_evaluation.opponent_expected_chances:>12.4f}"
                f"{effects.our_chance_multiplier:>12.4f}"
                f"{effects.opponent_chance_multiplier:>12.4f}"
                f"{effects.counter_attack_chances:>12.4f}"
                f"{effects.special_event_multiplier:>12.4f}"
                f"{effects.long_shot_conversion_rate:>12.4f}"
            )

        print("=" * 170)

        print()
        print("TACTIC DISTRIBUTIONS")
        print("=" * 100)

        print(
            f"{'TACTIC':<24}"
            f"{'LEFT':>15}"
            f"{'CENTER':>15}"
            f"{'RIGHT':>15}"
        )

        print("-" * 100)

        for (
            tactic,
            context,
            effects,
            _,
            _
        ) in rows:

            print(
                f"{tactic.value:<24}"
                f"{effects.our_distribution.left:>15.4f}"
                f"{effects.our_distribution.center:>15.4f}"
                f"{effects.our_distribution.right:>15.4f}"
            )

        print("=" * 100)