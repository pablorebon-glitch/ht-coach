import pytest

from engine.optimizers.tactic_optimizer import (
    TacticOptimizer
)

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.player import Player
from models.position import Position
from models.side import Side
from models.tactic import Tactic
from models.team_ratings import TeamRatings


def make_player(
    name,
    passing,
    form=7
):

    return Player(
        name=name,
        age=25,
        days=0,
        speciality="",

        form=form,
        stamina=7,

        goalkeeper=1,
        defending=10,
        playmaking=10,
        winger=10,
        passing=passing,
        scoring=10,
        set_pieces=5,

        experience=5,
        leadership=5,

        tsi=1000,
        salary=1000
    )


def make_lineup(
    passing,
    form=7
):

    lineup = Lineup()

    lineup.players.append(
        LineupPlayer(
            player=make_player(
                "Goalkeeper",
                passing=20,
                form=form
            ),
            position=Position.GOALKEEPER,
            side=Side.CENTER
        )
    )

    for index in range(10):

        lineup.players.append(
            LineupPlayer(
                player=make_player(
                    f"Field Player {index}",
                    passing=passing,
                    form=form
                ),
                position=Position.INNER_MIDFIELDER,
                side=Side.CENTER
            )
        )

    return lineup


@pytest.fixture
def balanced_team():

    return TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=24,
        midfield=45,
        left_attack=25,
        central_attack=30,
        right_attack=24
    )


@pytest.fixture
def balanced_opponent():

    return TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=24,
        midfield=40,
        left_attack=25,
        central_attack=30,
        right_attack=24
    )


def test_optimizer_tests_all_tactics(
    balanced_team,
    balanced_opponent
):

    result = TacticOptimizer.optimize(
        balanced_team,
        balanced_opponent
    )

    assert (
        result.tested_tactics
        == len(
            TacticOptimizer.ALLOWED_TACTICS
        )
    )


def test_optimizer_returns_allowed_tactic(
    balanced_team,
    balanced_opponent
):

    result = TacticOptimizer.optimize(
        balanced_team,
        balanced_opponent
    )

    assert (
        result.tactic
        in TacticOptimizer.ALLOWED_TACTICS
    )


def test_optimizer_does_not_reduce_win_probability(
    balanced_team,
    balanced_opponent
):

    result = TacticOptimizer.optimize(
        balanced_team,
        balanced_opponent
    )

    assert (
        result.probabilities.win
        >= result.baseline_win_probability
    )


def test_probabilities_sum_to_one(
    balanced_team,
    balanced_opponent
):

    result = TacticOptimizer.optimize(
        balanced_team,
        balanced_opponent
    )

    total = (
        result.probabilities.win
        + result.probabilities.draw
        + result.probabilities.loss
    )

    assert total == pytest.approx(
        1.0,
        abs=1e-6
    )


def test_normal_tactic_is_available():

    assert (
        Tactic.NORMAL
        in TacticOptimizer.ALLOWED_TACTICS
    )


def test_optimizer_returns_complete_evaluation(
    balanced_team,
    balanced_opponent
):

    result = TacticOptimizer.optimize(
        balanced_team,
        balanced_opponent
    )

    assert result.ratings is not None

    assert result.match_evaluation is not None

    assert result.probabilities is not None


def test_optimizer_is_deterministic(
    balanced_team,
    balanced_opponent
):

    first_result = TacticOptimizer.optimize(
        balanced_team,
        balanced_opponent
    )

    second_result = TacticOptimizer.optimize(
        balanced_team,
        balanced_opponent
    )

    assert (
        first_result.tactic
        == second_result.tactic
    )

    assert (
        first_result.probabilities.win
        == pytest.approx(
            second_result.probabilities.win
        )
    )


def test_optimizer_accepts_lineup_for_tactic_level():

    lineup = make_lineup(
        passing=10
    )

    team = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=45,
        left_attack=20,
        central_attack=30,
        right_attack=20
    )

    opponent = TeamRatings(
        left_defense=25,
        central_defense=25,
        right_defense=25,
        midfield=40,
        left_attack=25,
        central_attack=25,
        right_attack=25
    )

    result = TacticOptimizer.optimize(
        team,
        opponent,
        lineup=lineup
    )

    assert result.tactic_level >= 0.0

    assert result.tactic_level <= 20.0


def test_normal_tactic_returns_zero_tactic_level():

    lineup = make_lineup(
        passing=10
    )

    team = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=45,
        left_attack=25,
        central_attack=25,
        right_attack=25
    )

    opponent = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=45,
        left_attack=25,
        central_attack=25,
        right_attack=25
    )

    result = TacticOptimizer.optimize(
        team,
        opponent,
        lineup=lineup
    )

    if result.tactic == Tactic.NORMAL:

        assert result.tactic_level == 0.0


def test_optimizer_with_lineup_is_deterministic():

    lineup = make_lineup(
        passing=12
    )

    team = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=45,
        left_attack=20,
        central_attack=35,
        right_attack=20
    )

    opponent = TeamRatings(
        left_defense=30,
        central_defense=20,
        right_defense=30,
        midfield=40,
        left_attack=25,
        central_attack=25,
        right_attack=25
    )

    first = TacticOptimizer.optimize(
        team,
        opponent,
        lineup=lineup
    )

    second = TacticOptimizer.optimize(
        team,
        opponent,
        lineup=lineup
    )

    assert first.tactic == second.tactic

    assert (
        first.tactic_level
        == second.tactic_level
    )

    assert (
        first.probabilities.win
        == pytest.approx(
            second.probabilities.win
        )
    )


def test_balanced_scenario_can_keep_normal_tactic():

    lineup = make_lineup(
        passing=10
    )

    team = TeamRatings(
        left_defense=30,
        central_defense=35,
        right_defense=30,
        midfield=45,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    opponent = TeamRatings(
        left_defense=30,
        central_defense=35,
        right_defense=30,
        midfield=45,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    result = TacticOptimizer.optimize(
        team,
        opponent,
        lineup=lineup
    )

    assert result.tactic == Tactic.NORMAL

    assert result.tactic_level == 0.0


def test_weak_central_defense_can_favor_attack_in_middle():

    lineup = make_lineup(
        passing=20,
        form=8
    )

    team = TeamRatings(
        left_defense=40,
        central_defense=45,
        right_defense=40,
        midfield=50,
        left_attack=10,
        central_attack=55,
        right_attack=10
    )

    opponent = TeamRatings(
        left_defense=60,
        central_defense=5,
        right_defense=60,
        midfield=45,
        left_attack=15,
        central_attack=15,
        right_attack=15
    )

    result = TacticOptimizer.optimize(
        team,
        opponent,
        lineup=lineup
    )

    assert (
        result.tactic
        == Tactic.ATTACK_IN_MIDDLE
    )

    assert result.tactic_level > 0.0

    assert (
        result.probabilities.win
        > result.baseline_win_probability
    )


def test_weak_wing_defenses_can_favor_attack_on_wings():

    lineup = make_lineup(
        passing=20,
        form=8
    )

    team = TeamRatings(
        left_defense=40,
        central_defense=50,
        right_defense=40,
        midfield=50,
        left_attack=55,
        central_attack=10,
        right_attack=55
    )

    opponent = TeamRatings(
        left_defense=5,
        central_defense=60,
        right_defense=5,
        midfield=45,
        left_attack=15,
        central_attack=15,
        right_attack=15
    )

    result = TacticOptimizer.optimize(
        team,
        opponent,
        lineup=lineup
    )

    assert (
        result.tactic
        == Tactic.ATTACK_ON_WINGS
    )

    assert result.tactic_level > 0.0

    assert (
        result.probabilities.win
        > result.baseline_win_probability
    )