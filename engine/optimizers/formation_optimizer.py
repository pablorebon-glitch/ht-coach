from dataclasses import dataclass

from engine.optimizers.lineup_optimizer import (
    LineupOptimizer
)

from engine.optimizers.tactic_optimizer import (
    TacticOptimizer
)

from engine.analyzers.team_rater import (
    TeamRater
)

from engine.analyzers.formation_analyzer import (
    FormationAnalyzer
)


@dataclass
class FormationMatchResult:

    formation: object

    lineup: object

    tactic: object

    tactic_level: float

    ratings: object

    match_evaluation: object

    probabilities: object

    tested_lineups: int

    tested_order_configurations: int

    order_finalists: int

    tested_tactics: int

    baseline_win_probability: float

    best_normal_win_probability: float

    best_order_win_probability: float

    objective_trace: object = None

    objective_frontier: tuple = ()


class FormationOptimizer:

    @staticmethod
    def optimize(
        players,
        formations
    ):

        results = []

        for formation in formations:

            lineup = (
                LineupOptimizer.optimize(
                    players,
                    formation
                )
            )

            ratings = TeamRater.calculate(
                lineup
            )

            score = (
                FormationAnalyzer.overall_score(
                    ratings
                )
            )

            results.append(
                (
                    formation,
                    lineup,
                    ratings,
                    score
                )
            )

        results.sort(
            key=lambda x: x[3],
            reverse=True
        )

        return results

    @staticmethod
    def optimize_against(
        players,
        formations,
        opponent_ratings,
        config=None
    ):

        results = []

        for formation in formations:

            # -------------------------------------------------
            # STEP 1
            # OPTIMIZE LINEUP + INDIVIDUAL ORDERS
            #
            # IMPORTANT:
            # config must be propagated here so candidate XI
            # evaluation and order optimization use the same
            # match model configuration as tactic optimization.
            # -------------------------------------------------

            lineup_optimization = (
                LineupOptimizer.optimize_against(
                    players,
                    formation,
                    opponent_ratings,
                    config=config
                )
            )

            # -------------------------------------------------
            # STEP 2
            # FREEZE PIPELINE STAGE VALUES
            #
            # These values represent:
            #
            # baseline:
            # heuristic starting XI with Normal orders
            #
            # best normal:
            # best candidate XI before individual orders
            #
            # best order:
            # best candidate XI after individual orders
            #
            # These values must be frozen before team tactics
            # are evaluated.
            # -------------------------------------------------

            baseline_win_probability = float(
                lineup_optimization
                .baseline_win_probability
            )

            best_normal_win_probability = float(
                lineup_optimization
                .best_normal_win_probability
            )

            best_order_win_probability = float(
                lineup_optimization
                .best_order_win_probability
            )

            optimized_lineup = (
                lineup_optimization.lineup
            )

            optimized_ratings = (
                lineup_optimization.ratings
            )

            # -------------------------------------------------
            # STEP 3
            # OPTIMIZE TEAM TACTIC
            #
            # The same config is propagated to tactic
            # optimization.
            # -------------------------------------------------

            tactic_arguments = {
                "lineup": optimized_lineup
            }

            if config is not None:

                tactic_arguments["config"] = (
                    config
                )

            tactic_optimization = (
                TacticOptimizer.optimize(
                    optimized_ratings,
                    opponent_ratings,
                    **tactic_arguments
                )
            )

            # -------------------------------------------------
            # STEP 4
            # BUILD COMPLETE RESULT
            # -------------------------------------------------

            result = FormationMatchResult(

                formation=formation,

                lineup=optimized_lineup,

                tactic=(
                    tactic_optimization.tactic
                ),

                tactic_level=(
                    tactic_optimization.tactic_level
                ),

                ratings=(
                    tactic_optimization.ratings
                ),

                match_evaluation=(
                    tactic_optimization
                    .match_evaluation
                ),

                probabilities=(
                    tactic_optimization.probabilities
                ),

                tested_lineups=(
                    lineup_optimization
                    .tested_lineups
                ),

                tested_order_configurations=(
                    lineup_optimization
                    .tested_order_configurations
                ),

                order_finalists=(
                    lineup_optimization
                    .order_finalists
                ),

                tested_tactics=(
                    tactic_optimization
                    .tested_tactics
                ),

                baseline_win_probability=(
                    baseline_win_probability
                ),

                best_normal_win_probability=(
                    best_normal_win_probability
                ),

                best_order_win_probability=(
                    best_order_win_probability
                ),

                objective_trace=(
                    lineup_optimization
                    .objective_trace
                ),

                objective_frontier=(
                    lineup_optimization
                    .objective_frontier
                )
            )

            results.append(
                result
            )

        # -------------------------------------------------
        # BEST FORMATION AFTER COMPLETE PIPELINE
        # -------------------------------------------------

        results.sort(
            key=lambda result: (
                result.probabilities.win
            ),
            reverse=True
        )

        return results
