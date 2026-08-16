from dataclasses import dataclass
from itertools import combinations

from engine.analyzers.player_analyzer import PlayerAnalyzer
from engine.generators.candidate_lineup_generator import CandidateLineupGenerator
from engine.optimizers.formation_optimizer import FormationMatchResult
from engine.optimizers.lineup_optimizer import (
    LineupOptimizationResult,
    LineupOptimizer,
)
from engine.optimizers.lineup_objective import LineupObjectiveEvaluator
from engine.optimizers.order_optimizer import OrderOptimizer
from engine.optimizers.tactic_optimizer import TacticOptimizer
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.tactic import Tactic


@dataclass
class ConstrainedOptimizationResult:

    optimization: LineupOptimizationResult

    locked_players: tuple

    unplaced_required_players: tuple


class TrainingConstrainedLineupOptimizer:
    """
    Optimizes a lineup against an opponent while guaranteeing that a given
    set of "required" players (players who still need weekly training
    minutes) start in a training-eligible slot for the active training
    type.

    Training always wins over competitiveness: required players are
    locked into the best-fitting training slots first, and only the
    remaining slots are optimized for the matchup against the opponent.
    If there are more required players than training-eligible slots in
    the formation, as many as possible are locked in and the rest are
    reported back as unplaced instead of being silently dropped.
    """

    DEFAULT_CANDIDATES_PER_ROLE = CandidateLineupGenerator.DEFAULT_CANDIDATES_PER_ROLE

    DEFAULT_BEAM_WIDTH = CandidateLineupGenerator.DEFAULT_BEAM_WIDTH

    DEFAULT_ORDER_FINALISTS = LineupOptimizer.DEFAULT_ORDER_FINALISTS

    DEFAULT_ORDER_BEAM_WIDTH = LineupOptimizer.DEFAULT_ORDER_BEAM_WIDTH

    @classmethod
    def optimize_against(
        cls,
        players,
        formation,
        opponent_ratings,
        required_players,
        rules,
        order_finalists=None,
        order_beam_width=None,
        candidates_per_role=None,
        beam_width=None,
        config=None,
    ):
        order_finalists = order_finalists or cls.DEFAULT_ORDER_FINALISTS
        order_beam_width = order_beam_width or cls.DEFAULT_ORDER_BEAM_WIDTH
        candidates_per_role = candidates_per_role or cls.DEFAULT_CANDIDATES_PER_ROLE
        beam_width = beam_width or cls.DEFAULT_BEAM_WIDTH

        roles = LineupOptimizer._build_roles(formation)

        locked, unplaced = cls._lock_required_players(
            list(required_players),
            roles,
            rules,
        )

        locked_ids = {
            CandidateLineupGenerator._player_key(lineup_player.player)
            for lineup_player in locked
        }

        remaining_players = [
            player for player in players
            if CandidateLineupGenerator._player_key(player) not in locked_ids
        ]

        reduced_roles = cls._reduced_roles(roles, locked)

        candidate_partials = cls._generate_candidates(
            remaining_players,
            reduced_roles,
            candidates_per_role,
            beam_width,
        )

        baseline_players = cls._build_baseline(remaining_players, reduced_roles)

        full_candidates = [
            Lineup(players=list(locked) + list(partial))
            for partial in candidate_partials
        ]
        baseline_lineup = Lineup(players=list(locked) + list(baseline_players))

        evaluated = []
        for lineup in full_candidates:
            ratings, match_evaluation, probabilities = (
                LineupOptimizer._evaluate_lineup(
                    lineup,
                    opponent_ratings,
                    config=config,
                )
            )
            evaluated.append((lineup, ratings, match_evaluation, probabilities))

        (
            baseline_ratings,
            baseline_match_evaluation,
            baseline_probabilities,
        ) = LineupOptimizer._evaluate_lineup(
            baseline_lineup,
            opponent_ratings,
            config=config,
        )
        evaluated.append(
            (
                baseline_lineup,
                baseline_ratings,
                baseline_match_evaluation,
                baseline_probabilities,
            )
        )

        tested_lineups = len(evaluated)

        evaluated.sort(key=lambda item: item[3].win, reverse=True)

        best_lineup, best_ratings, best_match_evaluation, best_probabilities = (
            evaluated[0]
        )
        best_normal_win_probability = best_probabilities.win
        best_order_win_probability = best_normal_win_probability

        finalists = evaluated[:order_finalists]
        tested_order_configurations = 0

        for lineup, ratings, match_evaluation, probabilities in finalists:
            order_optimization = OrderOptimizer.optimize(
                lineup,
                opponent_ratings,
                beam_width=order_beam_width,
                config=config,
            )

            tested_order_configurations += order_optimization.tested_configurations

            if order_optimization.probabilities.win > best_order_win_probability:
                best_order_win_probability = order_optimization.probabilities.win
                best_lineup = order_optimization.lineup
                best_ratings = order_optimization.ratings
                best_match_evaluation = order_optimization.match_evaluation
                best_probabilities = order_optimization.probabilities

        optimization = LineupOptimizationResult(
            lineup=best_lineup,
            tactic=Tactic.NORMAL,
            tactic_level=0.0,
            ratings=best_ratings,
            match_evaluation=best_match_evaluation,
            probabilities=best_probabilities,
            tested_lineups=tested_lineups,
            tested_order_configurations=tested_order_configurations,
            order_finalists=len(finalists),
            tested_tactics=0,
            baseline_win_probability=baseline_probabilities.win,
            best_normal_win_probability=best_normal_win_probability,
            best_order_win_probability=best_order_win_probability,
            objective_trace=LineupObjectiveEvaluator.evaluate_lineup(
                best_lineup,
                opponent_ratings,
                candidate_id="training-constrained",
                config=config,
            ),
        )

        return ConstrainedOptimizationResult(
            optimization=optimization,
            locked_players=tuple(lineup_player.player for lineup_player in locked),
            unplaced_required_players=tuple(unplaced),
        )

    @staticmethod
    def _lock_required_players(required_players, roles, rules):
        trainable_slots = []
        for position, side, amount in roles:
            factor = rules.factor_for_position(position)
            if factor <= 0:
                continue
            for _ in range(int(amount)):
                trainable_slots.append((position, side, float(factor)))

        # Fill the highest-value training slots (e.g. full-training
        # midfield roles) before lower-value ones (e.g. half-training
        # wingers), so required players land where their training counts
        # for the most.
        trainable_slots.sort(key=lambda slot: (-slot[2], slot[0].value, slot[1].value))

        remaining = list(required_players)
        locked = []

        for position, side, _factor in trainable_slots:
            if not remaining:
                break

            ranking = PlayerAnalyzer.rank_players(remaining, position.value, side)
            if not ranking:
                continue

            best_player = ranking[0].player
            locked.append(
                LineupPlayer(player=best_player, position=position, side=side)
            )
            remaining = [
                player for player in remaining
                if CandidateLineupGenerator._player_key(player)
                != CandidateLineupGenerator._player_key(best_player)
            ]

        return locked, tuple(remaining)

    @staticmethod
    def _reduced_roles(roles, locked):
        used = {}
        for lineup_player in locked:
            key = (lineup_player.position, lineup_player.side)
            used[key] = used.get(key, 0) + 1

        reduced = []
        for position, side, amount in roles:
            key = (position, side)
            taken = used.get(key, 0)
            reduced.append((position, side, max(0, int(amount) - taken)))
            if taken:
                used[key] = 0

        return reduced

    @classmethod
    def _generate_candidates(cls, players, roles, candidates_per_role, beam_width):
        rankings = CandidateLineupGenerator._build_rankings(
            players,
            roles,
            candidates_per_role,
        )

        Partial = type(
            "Partial",
            (),
            {},
        )

        beam = [([], frozenset(), 0.0)]

        for position, side, amount in roles:
            ranking = rankings[(position, side)]
            player_combinations = list(combinations(ranking, int(amount)))

            next_beam = []
            for players_list, used_ids, score in beam:
                for player_scores in player_combinations:
                    selected_ids = frozenset(
                        CandidateLineupGenerator._player_key(player_score.player)
                        for player_score in player_scores
                    )

                    if used_ids & selected_ids:
                        continue

                    new_players = players_list + [
                        LineupPlayer(
                            player=player_score.player,
                            position=position,
                            side=side,
                        )
                        for player_score in player_scores
                    ]

                    new_score = score + sum(
                        player_score.score for player_score in player_scores
                    )

                    next_beam.append(
                        (new_players, used_ids | selected_ids, new_score)
                    )

            next_beam.sort(key=lambda item: item[2], reverse=True)
            beam = next_beam[:beam_width]

            if not beam:
                break

        expected_player_count = sum(int(amount) for _, _, amount in roles)

        candidates = []
        seen = set()
        for players_list, _used_ids, _score in beam:
            if len(players_list) != expected_player_count:
                continue

            key = tuple(
                sorted(
                    (
                        CandidateLineupGenerator._player_key(lp.player),
                        lp.position.value,
                        lp.side.value,
                    )
                    for lp in players_list
                )
            )
            if key in seen:
                continue
            seen.add(key)
            candidates.append(players_list)

        return candidates

    @staticmethod
    def _build_baseline(players, roles):
        lineup_players = []
        available_players = list(players)

        for position, side, amount in roles:
            ranking = PlayerAnalyzer.rank_players(available_players, position.value, side)
            for player_score in ranking[: int(amount)]:
                lineup_players.append(
                    LineupPlayer(
                        player=player_score.player,
                        position=position,
                        side=side,
                    )
                )
                available_players.remove(player_score.player)

        return lineup_players


@dataclass
class FormationTrainingConstraintResult:

    formation_result: FormationMatchResult

    unplaced_required_players: tuple


class TrainingConstrainedFormationOptimizer:
    """
    Formation-level counterpart of TrainingConstrainedLineupOptimizer.

    Mirrors FormationOptimizer.optimize_against (lineup + individual
    orders + team tactic, evaluated against the opponent) but guarantees
    that every "required" player (still owed weekly training minutes)
    starts in a training-eligible slot, for every formation being
    compared.
    """

    @staticmethod
    def optimize_against(
        players,
        formations,
        opponent_ratings,
        required_players,
        rules,
        config=None,
    ):
        results = []

        for formation in formations:
            constrained = TrainingConstrainedLineupOptimizer.optimize_against(
                players,
                formation,
                opponent_ratings,
                required_players,
                rules,
                config=config,
            )

            lineup_optimization = constrained.optimization

            tactic_arguments = {"lineup": lineup_optimization.lineup}
            if config is not None:
                tactic_arguments["config"] = config

            tactic_optimization = TacticOptimizer.optimize(
                lineup_optimization.ratings,
                opponent_ratings,
                **tactic_arguments,
            )

            formation_result = FormationMatchResult(
                formation=formation,
                lineup=lineup_optimization.lineup,
                tactic=tactic_optimization.tactic,
                tactic_level=tactic_optimization.tactic_level,
                ratings=tactic_optimization.ratings,
                match_evaluation=tactic_optimization.match_evaluation,
                probabilities=tactic_optimization.probabilities,
                tested_lineups=lineup_optimization.tested_lineups,
                tested_order_configurations=lineup_optimization.tested_order_configurations,
                order_finalists=lineup_optimization.order_finalists,
                tested_tactics=tactic_optimization.tested_tactics,
                baseline_win_probability=lineup_optimization.baseline_win_probability,
                best_normal_win_probability=lineup_optimization.best_normal_win_probability,
                best_order_win_probability=lineup_optimization.best_order_win_probability,
                objective_trace=lineup_optimization.objective_trace,
                objective_frontier=lineup_optimization.objective_frontier,
            )

            results.append(
                FormationTrainingConstraintResult(
                    formation_result=formation_result,
                    unplaced_required_players=constrained.unplaced_required_players,
                )
            )

        results.sort(
            key=lambda item: item.formation_result.probabilities.win,
            reverse=True,
        )

        return results
