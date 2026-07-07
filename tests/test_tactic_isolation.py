import pytest

from engine.optimizers.tactic_optimizer import (
    TacticOptimizer
)

from models.tactic import Tactic

from models.team_ratings import (
    TeamRatings
)


@pytest.fixture
def team():

    return TeamRatings(
        left_defense=30,
        central_defense=35,
        right_defense=30,
        midfield=45,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )


@pytest.fixture
def opponent():

    return TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=40,
        left_attack=25,
        central_attack=30,
        right_attack=25
    )


def ratings_signature(
    ratings
):

    return (
        ratings.left_defense,
        ratings.central_defense,
        ratings.right_defense,
        ratings.midfield,
        ratings.left_attack,
        ratings.central_attack,
        ratings.right_attack
    )


def test_normal_evaluation_does_not_modify_base_ratings(
    team,
    opponent
):

    original_signature = (
        ratings_signature(
            team
        )
    )

    TacticOptimizer._evaluate(
        team,
        Tactic.NORMAL,
        opponent
    )

    assert (
        ratings_signature(team)
        == original_signature
    )


@pytest.mark.parametrize(
    "tactic",
    tuple(Tactic)
)
def test_tactic_evaluation_does_not_modify_base_ratings(
    team,
    opponent,
    tactic
):

    original_signature = (
        ratings_signature(
            team
        )
    )

    TacticOptimizer._evaluate(
        team,
        tactic,
        opponent
    )

    assert (
        ratings_signature(team)
        == original_signature
    )


@pytest.mark.parametrize(
    "tactic",
    tuple(Tactic)
)
def test_tactic_evaluation_does_not_modify_opponent_ratings(
    team,
    opponent,
    tactic
):

    original_signature = (
        ratings_signature(
            opponent
        )
    )

    TacticOptimizer._evaluate(
        team,
        tactic,
        opponent
    )

    assert (
        ratings_signature(opponent)
        == original_signature
    )


def test_normal_result_is_same_before_and_after_other_tactics(
    team,
    opponent
):

    (
        _,
        _,
        first_match_evaluation,
        first_probabilities
    ) = TacticOptimizer._evaluate(
        team,
        Tactic.NORMAL,
        opponent
    )

    for tactic in Tactic:

        TacticOptimizer._evaluate(
            team,
            tactic,
            opponent
        )

    (
        _,
        _,
        second_match_evaluation,
        second_probabilities
    ) = TacticOptimizer._evaluate(
        team,
        Tactic.NORMAL,
        opponent
    )

    assert (
        second_match_evaluation.expected_goals
        == pytest.approx(
            first_match_evaluation.expected_goals
        )
    )

    assert (
        second_match_evaluation.opponent_expected_goals
        == pytest.approx(
            first_match_evaluation.opponent_expected_goals
        )
    )

    assert (
        second_probabilities.win
        == pytest.approx(
            first_probabilities.win
        )
    )

    assert (
        second_probabilities.draw
        == pytest.approx(
            first_probabilities.draw
        )
    )

    assert (
        second_probabilities.loss
        == pytest.approx(
            first_probabilities.loss
        )
    )


def test_each_tactic_receives_independent_ratings_object(
    team,
    opponent
):

    (
        _,
        normal_effects,
        _,
        _
    ) = TacticOptimizer._evaluate(
        team,
        Tactic.NORMAL,
        opponent
    )

    (
        _,
        creative_effects,
        _,
        _
    ) = TacticOptimizer._evaluate(
        team,
        Tactic.PLAY_CREATIVELY,
        opponent
    )

    assert (
        normal_effects.ratings
        is not team
    )

    assert (
        creative_effects.ratings
        is not team
    )

    assert (
        normal_effects.ratings
        is not creative_effects.ratings
    )


def test_optimizer_does_not_modify_base_ratings(
    team,
    opponent
):

    original_team_signature = (
        ratings_signature(
            team
        )
    )

    original_opponent_signature = (
        ratings_signature(
            opponent
        )
    )

    TacticOptimizer.optimize(
        team,
        opponent
    )

    assert (
        ratings_signature(team)
        == original_team_signature
    )

    assert (
        ratings_signature(opponent)
        == original_opponent_signature
    )


def test_optimizer_is_repeatable_with_same_objects(
    team,
    opponent
):

    first = TacticOptimizer.optimize(
        team,
        opponent
    )

    second = TacticOptimizer.optimize(
        team,
        opponent
    )

    assert (
        first.tactic
        == second.tactic
    )

    assert (
        first.tactic_level
        == pytest.approx(
            second.tactic_level
        )
    )

    assert (
        first.probabilities.win
        == pytest.approx(
            second.probabilities.win
        )
    )

    assert (
        first.probabilities.draw
        == pytest.approx(
            second.probabilities.draw
        )
    )

    assert (
        first.probabilities.loss
        == pytest.approx(
            second.probabilities.loss
        )
    )