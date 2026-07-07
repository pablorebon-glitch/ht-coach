import pytest

from importers.csv_importer import load_players

from engine.optimizers.formation_optimizer import (
    FormationOptimizer
)

from models.formations import FORMATIONS
from models.team_ratings import TeamRatings


@pytest.fixture(scope="module")
def players():

    return load_players(
        "players.csv"
    )


@pytest.fixture(scope="module")
def opponent_profiles():

    return {

        "strong_left_attack": TeamRatings(
            left_defense=25,
            central_defense=25,
            right_defense=25,
            midfield=40,
            left_attack=50,
            central_attack=25,
            right_attack=15
        ),

        "strong_right_attack": TeamRatings(
            left_defense=25,
            central_defense=25,
            right_defense=25,
            midfield=40,
            left_attack=15,
            central_attack=25,
            right_attack=50
        ),

        "strong_midfield": TeamRatings(
            left_defense=25,
            central_defense=25,
            right_defense=25,
            midfield=60,
            left_attack=25,
            central_attack=25,
            right_attack=25
        ),

        "weak_central_defense": TeamRatings(
            left_defense=40,
            central_defense=10,
            right_defense=40,
            midfield=40,
            left_attack=25,
            central_attack=25,
            right_attack=25
        ),

        "weak_wing_defenses": TeamRatings(
            left_defense=10,
            central_defense=45,
            right_defense=10,
            midfield=40,
            left_attack=25,
            central_attack=25,
            right_attack=25
        ),
    }


@pytest.fixture(scope="module")
def optimization_results(
    players,
    opponent_profiles
):

    results = {}

    for profile_name, opponent in (
        opponent_profiles.items()
    ):

        results[profile_name] = (
            FormationOptimizer.optimize_against(
                players,
                FORMATIONS,
                opponent
            )
        )

    return results


def lineup_signature(lineup):

    return tuple(
        sorted(
            (
                lineup_player.player.name,
                lineup_player.position.value,
                lineup_player.side.value,
                lineup_player.order.value,
                (
                    lineup_player.order_side.value
                    if lineup_player.order_side
                    is not None
                    else None
                )
            )
            for lineup_player
            in lineup.players
        )
    )


def test_all_profiles_return_results(
    optimization_results,
    opponent_profiles
):

    assert (
        set(optimization_results)
        == set(opponent_profiles)
    )

    for results in (
        optimization_results.values()
    ):

        assert len(results) == len(
            FORMATIONS
        )


def test_results_are_sorted_by_win_probability(
    optimization_results
):

    for results in (
        optimization_results.values()
    ):

        win_probabilities = [
            result.probabilities.win
            for result in results
        ]

        assert win_probabilities == sorted(
            win_probabilities,
            reverse=True
        )


def test_all_optimized_lineups_are_complete(
    optimization_results
):

    for results in (
        optimization_results.values()
    ):

        for result in results:

            assert len(
                result.lineup.players
            ) == 11


def test_probabilities_sum_to_one(
    optimization_results
):

    for results in (
        optimization_results.values()
    ):

        for result in results:

            total = (
                result.probabilities.win
                + result.probabilities.draw
                + result.probabilities.loss
            )

            assert total == pytest.approx(
                1.0,
                abs=1e-6
            )


def test_optimization_never_reduces_baseline_win(
    optimization_results
):

    for results in (
        optimization_results.values()
    ):

        for result in results:

            assert (
                result.probabilities.win
                >= result.baseline_win_probability
            )


def test_order_optimization_never_reduces_best_normal_win(
    optimization_results
):

    for results in (
        optimization_results.values()
    ):

        for result in results:

            assert (
                result.probabilities.win
                >= (
                    result.best_normal_win_probability
                )
            )


def test_optimizer_evaluates_candidates_and_orders(
    optimization_results
):

    for results in (
        optimization_results.values()
    ):

        for result in results:

            assert (
                result.tested_lineups
                > 0
            )

            assert (
                result.order_finalists
                > 0
            )

            assert (
                result.tested_order_configurations
                > 0
            )


def test_different_opponents_produce_tactical_adaptation(
    optimization_results
):

    best_signatures = {

        profile_name: lineup_signature(
            results[0].lineup
        )

        for profile_name, results
        in optimization_results.items()
    }

    unique_signatures = set(
        best_signatures.values()
    )

    assert len(unique_signatures) > 1


def test_opposite_flank_threats_produce_different_solution(
    optimization_results
):

    left_result = optimization_results[
        "strong_left_attack"
    ][0]

    right_result = optimization_results[
        "strong_right_attack"
    ][0]

    left_signature = lineup_signature(
        left_result.lineup
    )

    right_signature = lineup_signature(
        right_result.lineup
    )

    assert (
        left_signature
        != right_signature
    )


def test_central_and_wing_defensive_weaknesses_produce_different_solution(
    optimization_results
):

    central_result = optimization_results[
        "weak_central_defense"
    ][0]

    wing_result = optimization_results[
        "weak_wing_defenses"
    ][0]

    central_signature = lineup_signature(
        central_result.lineup
    )

    wing_signature = lineup_signature(
        wing_result.lineup
    )

    assert (
        central_signature
        != wing_signature
    )