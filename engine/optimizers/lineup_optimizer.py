from dataclasses import dataclass

from engine.analyzers.team_rater import (
    TeamRater
)

from engine.analyzers.player_analyzer import (
    PlayerAnalyzer
)

from engine.evaluators.match_evaluator import (
    MatchEvaluator
)

from engine.evaluators.result_probability_evaluator import (
    ResultProbabilityEvaluator
)

from engine.generators.candidate_lineup_generator import (
    CandidateLineupGenerator
)

from engine.optimizers.order_optimizer import (
    OrderOptimizer
)

from engine.position_registry import (
    POSITION_ENGINES
)

from models.lineup import Lineup

from models.lineup_player import (
    LineupPlayer
)

from models.position import Position

from models.side import Side

from models.tactic import Tactic


@dataclass
class LineupOptimizationResult:

    lineup: object

    tactic: Tactic

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


@dataclass
class EvaluatedLineup:

    lineup: object

    ratings: object

    match_evaluation: object

    probabilities: object


class LineupOptimizer:

    DEFAULT_ORDER_FINALISTS = 10

    DEFAULT_ORDER_BEAM_WIDTH = 100

    @staticmethod
    def _build_roles(
        formation
    ):

        roles = []

        for (
            position,
            amount
        ) in formation.positions.items():

            if (
                position.value
                not in POSITION_ENGINES
            ):

                continue

            if (
                position
                in {
                    Position.WING_BACK,
                    Position.WINGER,
                }
                and amount == 2
            ):

                roles.append(
                    (
                        position,
                        Side.LEFT,
                        1
                    )
                )

                roles.append(
                    (
                        position,
                        Side.RIGHT,
                        1
                    )
                )

            elif (
                position
                in {
                    Position.WING_BACK,
                    Position.WINGER,
                }
                and amount == 1
            ):

                roles.append(
                    (
                        position,
                        Side.LEFT,
                        1
                    )
                )

            else:

                roles.append(
                    (
                        position,
                        Side.CENTER,
                        amount
                    )
                )

        return roles

    @classmethod
    def _build_lineup(
        cls,
        players,
        formation
    ):

        lineup = Lineup()

        available_players = (
            players.copy()
        )

        roles = cls._build_roles(
            formation
        )

        for (
            position,
            side,
            amount
        ) in roles:

            ranking = (
                PlayerAnalyzer.rank_players(
                    available_players,
                    position.value,
                    side
                )
            )

            for player_score in ranking[
                :amount
            ]:

                lineup.players.append(
                    LineupPlayer(
                        player=(
                            player_score.player
                        ),
                        position=position,
                        side=side
                    )
                )

                available_players.remove(
                    player_score.player
                )

        return lineup

    @staticmethod
    def _evaluate_lineup(
        lineup,
        opponent_ratings,
        config=None
    ):

        ratings = TeamRater.calculate(
            lineup
        )

        if config is None:

            match_evaluation = (
                MatchEvaluator.evaluate(
                    ratings,
                    opponent_ratings
                )
            )

        else:

            match_evaluation = (
                MatchEvaluator.evaluate(
                    ratings,
                    opponent_ratings,
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
            ratings,
            match_evaluation,
            probabilities
        )

    @classmethod
    def optimize(
        cls,
        players,
        formation
    ):

        return cls._build_lineup(
            players,
            formation
        )

    @classmethod
    def optimize_against(
        cls,
        players,
        formation,
        opponent_ratings,
        order_finalists=None,
        order_beam_width=None,
        config=None
    ):

        if order_finalists is None:

            order_finalists = (
                cls.DEFAULT_ORDER_FINALISTS
            )

        if order_beam_width is None:

            order_beam_width = (
                cls.DEFAULT_ORDER_BEAM_WIDTH
            )

        baseline_lineup = cls.optimize(
            players,
            formation
        )

        (
            baseline_ratings,
            baseline_match_evaluation,
            baseline_probabilities
        ) = cls._evaluate_lineup(
            baseline_lineup,
            opponent_ratings,
            config=config
        )

        candidate_lineups = (
            CandidateLineupGenerator.generate(
                players,
                formation
            )
        )

        tested_lineups = 0

        evaluated_lineups = []

        for lineup in candidate_lineups:

            tested_lineups += 1

            (
                ratings,
                match_evaluation,
                probabilities
            ) = cls._evaluate_lineup(
                lineup,
                opponent_ratings,
                config=config
            )

            evaluated_lineups.append(
                EvaluatedLineup(
                    lineup=lineup,
                    ratings=ratings,
                    match_evaluation=(
                        match_evaluation
                    ),
                    probabilities=probabilities
                )
            )

        evaluated_lineups.append(
            EvaluatedLineup(
                lineup=baseline_lineup,
                ratings=baseline_ratings,
                match_evaluation=(
                    baseline_match_evaluation
                ),
                probabilities=(
                    baseline_probabilities
                )
            )
        )

        evaluated_lineups.sort(
            key=lambda result: (
                result.probabilities.win
            ),
            reverse=True
        )

        best_normal_result = (
            evaluated_lineups[0]
        )

        finalists = evaluated_lineups[
            :order_finalists
        ]

        best_lineup = (
            best_normal_result.lineup
        )

        best_ratings = (
            best_normal_result.ratings
        )

        best_match_evaluation = (
            best_normal_result
            .match_evaluation
        )

        best_probabilities = (
            best_normal_result.probabilities
        )

        best_order_win_probability = (
            best_normal_result
            .probabilities
            .win
        )

        tested_order_configurations = 0

        for finalist in finalists:

            order_optimization = (
                OrderOptimizer.optimize(
                    finalist.lineup,
                    opponent_ratings,
                    beam_width=(
                        order_beam_width
                    ),
                    config=config
                )
            )

            tested_order_configurations += (
                order_optimization
                .tested_configurations
            )

            if (
                order_optimization
                .probabilities
                .win
                > best_order_win_probability
            ):

                best_order_win_probability = (
                    order_optimization
                    .probabilities
                    .win
                )

                best_lineup = (
                    order_optimization.lineup
                )

                best_ratings = (
                    order_optimization.ratings
                )

                best_match_evaluation = (
                    order_optimization
                    .match_evaluation
                )

                best_probabilities = (
                    order_optimization
                    .probabilities
                )

        return LineupOptimizationResult(

            lineup=best_lineup,

            tactic=Tactic.NORMAL,

            tactic_level=0.0,

            ratings=best_ratings,

            match_evaluation=(
                best_match_evaluation
            ),

            probabilities=(
                best_probabilities
            ),

            tested_lineups=(
                tested_lineups
            ),

            tested_order_configurations=(
                tested_order_configurations
            ),

            order_finalists=len(
                finalists
            ),

            tested_tactics=0,

            baseline_win_probability=(
                baseline_probabilities.win
            ),

            best_normal_win_probability=(
                best_normal_result
                .probabilities
                .win
            ),

            best_order_win_probability=(
                best_order_win_probability
            )
        )