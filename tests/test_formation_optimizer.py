import pytest

from importers.csv_importer import load_players

from models.formations import FORMATIONS
from models.team_ratings import TeamRatings

from engine.optimizers.formation_optimizer import (
    FormationOptimizer
)


@pytest.fixture(scope="module")
def players():

    return load_players(
        "players.csv"
    )


@pytest.fixture(scope="module")
def opponent():

    return TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=24,
        midfield=40,
        left_attack=25,
        central_attack=30,
        right_attack=24
    )


@pytest.fixture(scope="module")
def results(
    players,
    opponent
):

    return FormationOptimizer.optimize_against(
        players,
        FORMATIONS,
        opponent
    )


def test_optimizer_returns_one_result_per_formation(
    results
):

    assert len(results) == len(
        FORMATIONS
    )


def test_optimizer_results_are_sorted_by_win_probability(
    results
):

    win_probabilities = [
        result.probabilities.win
        for result in results
    ]

    assert win_probabilities == sorted(
        win_probabilities,
        reverse=True
    )


def test_every_result_has_complete_lineup(
    results
):

    for result in results:

        assert len(
            result.lineup.players
        ) == 11


def test_every_result_has_unique_players(
    results
):

    for result in results:

        player_ids = [
            id(lineup_player.player)
            for lineup_player
            in result.lineup.players
        ]

        assert len(player_ids) == len(
            set(player_ids)
        )


def test_result_probabilities_sum_to_one(
    results
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


def test_match_evaluation_has_valid_possession(
    results
):

    for result in results:

        assert (
            0.0
            <= result.match_evaluation.possession
            <= 1.0
        )


def test_expected_goals_are_non_negative(
    results
):

    for result in results:

        assert (
            result.match_evaluation.expected_goals
            >= 0
        )

        assert (
            result.match_evaluation.opponent_expected_goals
            >= 0
        )


def test_optimizer_evaluates_candidates(
    results
):

    for result in results:

        assert result.tested_lineups > 0


def test_best_result_matches_known_scenario(
    results
):

    best_result = results[0]

    assert best_result.formation.name == "3-5-2"

    assert (
        best_result.probabilities.win
        > best_result.probabilities.loss
    )


def test_best_result_contains_expected_core_players(
    results
):

    best_result = results[0]

    player_names = {
        lineup_player.player.name
        for lineup_player
        in best_result.lineup.players
    }

    expected_core = {
        "Ansu Fati",
        "Jae-Pyo Yang",
        "Feliciano Alvarez",
        "Mauricio Gustavo Bassedas",
        "Néstor 'El Barbas' Agusevich",
    }

    assert expected_core.issubset(
        player_names
    )