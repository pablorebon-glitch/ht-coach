import pytest

from engine.optimizers.tactic_optimizer import (
    TacticOptimizer
)

from engine.evaluators.match_evaluator import (
    MatchEvaluator
)

from models.match_model_config import (
    MatchModelConfig
)

from models.team_ratings import (
    TeamRatings
)


def make_team():

    return TeamRatings(
        left_defense=30,
        central_defense=35,
        right_defense=30,
        midfield=50,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )


def make_opponent():

    return TeamRatings(
        left_defense=30,
        central_defense=35,
        right_defense=30,
        midfield=40,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )


def test_default_config_matches_implicit_config():

    team = make_team()

    opponent = make_opponent()

    implicit_result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    explicit_result = MatchEvaluator.evaluate(
        team,
        opponent,
        config=MatchModelConfig()
    )

    assert (
        implicit_result.chance_probability
        == pytest.approx(
            explicit_result.chance_probability
        )
    )

    assert (
        implicit_result.expected_chances
        == pytest.approx(
            explicit_result.expected_chances
        )
    )

    assert (
        implicit_result.expected_goals
        == pytest.approx(
            explicit_result.expected_goals
        )
    )

    assert (
        implicit_result.opponent_expected_goals
        == pytest.approx(
            explicit_result.opponent_expected_goals
        )
    )


def test_midfield_exponent_changes_match_evaluation():

    team = make_team()

    opponent = make_opponent()

    low_exponent_config = MatchModelConfig(
        midfield_chance_share_exponent=1.0
    )

    high_exponent_config = MatchModelConfig(
        midfield_chance_share_exponent=3.0
    )

    low_result = MatchEvaluator.evaluate(
        team,
        opponent,
        config=low_exponent_config
    )

    high_result = MatchEvaluator.evaluate(
        team,
        opponent,
        config=high_exponent_config
    )

    assert (
        high_result.chance_probability
        > low_result.chance_probability
    )

    assert (
        high_result.expected_chances
        > low_result.expected_chances
    )

    assert (
        high_result.expected_goals
        > low_result.expected_goals
    )


def test_goal_conversion_factor_changes_expected_goals():

    team = make_team()

    opponent = make_opponent()

    low_conversion_config = MatchModelConfig(
        goal_conversion_factor=0.40
    )

    high_conversion_config = MatchModelConfig(
        goal_conversion_factor=1.20
    )

    low_result = MatchEvaluator.evaluate(
        team,
        opponent,
        config=low_conversion_config
    )

    high_result = MatchEvaluator.evaluate(
        team,
        opponent,
        config=high_conversion_config
    )

    assert (
        high_result.expected_goals
        > low_result.expected_goals
    )


def test_tactic_optimizer_receives_config():

    team = make_team()

    opponent = make_opponent()

    low_exponent_config = MatchModelConfig(
        midfield_chance_share_exponent=1.0
    )

    high_exponent_config = MatchModelConfig(
        midfield_chance_share_exponent=3.0
    )

    low_result = TacticOptimizer.optimize(
        team,
        opponent,
        config=low_exponent_config
    )

    high_result = TacticOptimizer.optimize(
        team,
        opponent,
        config=high_exponent_config
    )

    assert (
        high_result.match_evaluation
        .chance_probability

        > low_result.match_evaluation
        .chance_probability
    )

    assert (
        high_result.probabilities.win
        != pytest.approx(
            low_result.probabilities.win
        )
    )


def test_tactic_optimizer_is_deterministic_with_config():

    team = make_team()

    opponent = make_opponent()

    config = MatchModelConfig(
        midfield_chance_share_exponent=2.0,
        goal_conversion_factor=0.90
    )

    first_result = TacticOptimizer.optimize(
        team,
        opponent,
        config=config
    )

    second_result = TacticOptimizer.optimize(
        team,
        opponent,
        config=config
    )

    assert (
        first_result.tactic
        == second_result.tactic
    )

    assert (
        first_result.tactic_level
        == pytest.approx(
            second_result.tactic_level
        )
    )

    assert (
        first_result.match_evaluation
        .expected_goals

        == pytest.approx(
            second_result.match_evaluation
            .expected_goals
        )
    )

    assert (
        first_result.match_evaluation
        .opponent_expected_goals

        == pytest.approx(
            second_result.match_evaluation
            .opponent_expected_goals
        )
    )

    assert (
        first_result.probabilities.win
        == pytest.approx(
            second_result.probabilities.win
        )
    )


def test_config_does_not_mutate_ratings():

    team = make_team()

    opponent = make_opponent()

    original_team = make_team()

    original_opponent = make_opponent()

    config = MatchModelConfig(
        midfield_chance_share_exponent=2.5,
        goal_conversion_factor=0.90
    )

    TacticOptimizer.optimize(
        team,
        opponent,
        config=config
    )

    assert team == original_team

    assert opponent == original_opponent