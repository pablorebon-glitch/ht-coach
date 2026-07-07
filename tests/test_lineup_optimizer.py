from dataclasses import dataclass

import pytest

from engine.optimizers.lineup_optimizer import (
    LineupOptimizer
)

from models.player import Player
from models.team_ratings import TeamRatings
from models.tactic import Tactic

from models.formations import (
    FORMATION_352
)


def make_player(
    name,
    goalkeeper=1,
    defending=1,
    playmaking=1,
    winger=1,
    passing=1,
    scoring=1,
    set_pieces=1,
    form=7,
    stamina=7
):

    return Player(
        name=name,
        age=25,
        days=0,
        speciality="None",
        form=form,
        stamina=stamina,
        goalkeeper=goalkeeper,
        defending=defending,
        playmaking=playmaking,
        winger=winger,
        passing=passing,
        scoring=scoring,
        set_pieces=set_pieces,
        experience=5,
        leadership=5,
        tsi=10000,
        salary=10000
    )


@pytest.fixture
def players():

    return [

        make_player(
            "Goalkeeper",
            goalkeeper=18,
            defending=5
        ),

        make_player(
            "Central Defender 1",
            defending=17,
            passing=8,
            playmaking=7
        ),

        make_player(
            "Central Defender 2",
            defending=16,
            passing=9,
            playmaking=8
        ),

        make_player(
            "Central Defender 3",
            defending=15,
            passing=10,
            playmaking=9
        ),

        make_player(
            "Winger 1",
            winger=17,
            playmaking=13,
            passing=12
        ),

        make_player(
            "Winger 2",
            winger=16,
            playmaking=14,
            passing=13
        ),

        make_player(
            "Inner Midfielder 1",
            playmaking=18,
            passing=14,
            defending=10
        ),

        make_player(
            "Inner Midfielder 2",
            playmaking=17,
            passing=13,
            defending=11
        ),

        make_player(
            "Inner Midfielder 3",
            playmaking=16,
            passing=12,
            defending=12
        ),

        make_player(
            "Forward 1",
            scoring=18,
            passing=12
        ),

        make_player(
            "Forward 2",
            scoring=17,
            passing=13
        ),

        # --------------------------------------------------
        # SUBSTITUTES / ALTERNATIVE CANDIDATES
        # --------------------------------------------------

        make_player(
            "Defender Substitute",
            defending=14,
            passing=11
        ),

        make_player(
            "Winger Substitute",
            winger=15,
            playmaking=12,
            passing=14
        ),

        make_player(
            "Midfielder Substitute",
            playmaking=15,
            passing=15,
            defending=9
        ),

        make_player(
            "Forward Substitute",
            scoring=16,
            passing=14
        ),
    ]


@pytest.fixture
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


def optimize(players, opponent):

    return LineupOptimizer.optimize_against(
        players,
        FORMATION_352,
        opponent,
        order_finalists=3,
        order_beam_width=20
    )


def test_optimizer_returns_complete_lineup(
    players,
    opponent
):

    result = optimize(
        players,
        opponent
    )

    assert len(
        result.lineup.players
    ) == 11


def test_lineup_optimizer_does_not_optimize_tactics(
    players,
    opponent
):

    result = optimize(
        players,
        opponent
    )

    assert result.tactic == Tactic.NORMAL

    assert result.tactic_level == 0.0

    assert result.tested_tactics == 0


def test_result_probability_matches_best_order_probability(
    players,
    opponent
):

    result = optimize(
        players,
        opponent
    )

    assert (
        result.probabilities.win
        == pytest.approx(
            result.best_order_win_probability
        )
    )


def test_pipeline_probabilities_are_monotonic(
    players,
    opponent
):

    result = optimize(
        players,
        opponent
    )

    assert (
        result.best_normal_win_probability
        >= result.baseline_win_probability
    )

    assert (
        result.best_order_win_probability
        >= result.best_normal_win_probability
    )


def test_optimizer_reports_search_statistics(
    players,
    opponent
):

    result = optimize(
        players,
        opponent
    )

    assert result.tested_lineups > 0

    assert result.order_finalists == 3

    assert (
        result.tested_order_configurations
        > 0
    )


def test_optimizer_returns_complete_evaluation(
    players,
    opponent
):

    result = optimize(
        players,
        opponent
    )

    assert result.ratings is not None

    assert result.match_evaluation is not None

    assert result.probabilities is not None


def test_optimizer_is_deterministic(
    players,
    opponent
):

    first = optimize(
        players,
        opponent
    )

    second = optimize(
        players,
        opponent
    )

    assert [
        lineup_player.player.name
        for lineup_player
        in first.lineup.players
    ] == [
        lineup_player.player.name
        for lineup_player
        in second.lineup.players
    ]

    assert [
        lineup_player.order
        for lineup_player
        in first.lineup.players
    ] == [
        lineup_player.order
        for lineup_player
        in second.lineup.players
    ]

    assert (
        first.probabilities.win
        == pytest.approx(
            second.probabilities.win
        )
    )


def test_returned_lineup_evaluation_matches_result(
    players,
    opponent
):

    (
        ratings,
        match_evaluation,
        probabilities
    ) = LineupOptimizer._evaluate_lineup(
        optimize(
            players,
            opponent
        ).lineup,
        opponent
    )

    result = optimize(
        players,
        opponent
    )

    assert (
        probabilities.win
        == pytest.approx(
            result.probabilities.win
        )
    )

    assert (
        match_evaluation.expected_goals
        == pytest.approx(
            result.match_evaluation.expected_goals
        )
    )

    assert (
        ratings.midfield
        == pytest.approx(
            result.ratings.midfield
        )
    )