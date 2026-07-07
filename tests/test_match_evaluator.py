import pytest

from engine.evaluators.match_evaluator import MatchEvaluator
from engine.evaluators.result_probability_evaluator import (
    ResultProbabilityEvaluator
)

from models.team_ratings import TeamRatings
from models.chance_distribution import ChanceDistribution


def test_equal_midfields_have_equal_chance_probability():

    team = TeamRatings(
        midfield=40
    )

    opponent = TeamRatings(
        midfield=40
    )

    result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    assert result.chance_probability == pytest.approx(
        0.5
    )

    assert (
        result.opponent_chance_probability
        == pytest.approx(0.5)
    )


def test_chance_probabilities_sum_to_one():

    team = TeamRatings(
        midfield=45
    )

    opponent = TeamRatings(
        midfield=35
    )

    result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    assert (
        result.chance_probability
        + result.opponent_chance_probability
    ) == pytest.approx(1.0)


def test_expected_chances_sum_to_ten():

    team = TeamRatings(
        midfield=45
    )

    opponent = TeamRatings(
        midfield=35
    )

    result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    assert (
        result.expected_chances
        + result.opponent_expected_chances
    ) == pytest.approx(10.0)


def test_stronger_midfield_gets_more_expected_chances():

    team = TeamRatings(
        midfield=50
    )

    opponent = TeamRatings(
        midfield=30
    )

    result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    assert (
        result.expected_chances
        > result.opponent_expected_chances
    )


def test_stronger_attack_has_higher_conversion():

    strong_team = TeamRatings(
        midfield=40,
        central_attack=50
    )

    weak_team = TeamRatings(
        midfield=40,
        central_attack=20
    )

    opponent = TeamRatings(
        midfield=40,
        central_defense=30
    )

    strong_result = MatchEvaluator.evaluate(
        strong_team,
        opponent
    )

    weak_result = MatchEvaluator.evaluate(
        weak_team,
        opponent
    )

    assert (
        strong_result.central_conversion
        > weak_result.central_conversion
    )


def test_equal_teams_have_equal_expected_goals():

    team = TeamRatings(
        left_defense=30,
        central_defense=30,
        right_defense=30,
        midfield=40,
        left_attack=30,
        central_attack=30,
        right_attack=30
    )

    opponent = TeamRatings(
        left_defense=30,
        central_defense=30,
        right_defense=30,
        midfield=40,
        left_attack=30,
        central_attack=30,
        right_attack=30
    )

    result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    assert (
        result.expected_goals
        == pytest.approx(
            result.opponent_expected_goals
        )
    )


def test_stronger_team_has_higher_expected_goals():

    team = TeamRatings(
        left_defense=35,
        central_defense=40,
        right_defense=35,
        midfield=50,
        left_attack=40,
        central_attack=45,
        right_attack=40
    )

    opponent = TeamRatings(
        left_defense=25,
        central_defense=30,
        right_defense=25,
        midfield=35,
        left_attack=25,
        central_attack=30,
        right_attack=25
    )

    result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    assert (
        result.expected_goals
        > result.opponent_expected_goals
    )


def test_result_probabilities_sum_to_one():

    probabilities = (
        ResultProbabilityEvaluator.evaluate(
            expected_goals=2.5,
            opponent_expected_goals=1.5
        )
    )

    assert (
        probabilities.win
        + probabilities.draw
        + probabilities.loss
    ) == pytest.approx(1.0)


def test_equal_expected_goals_have_equal_win_and_loss():

    probabilities = (
        ResultProbabilityEvaluator.evaluate(
            expected_goals=2.0,
            opponent_expected_goals=2.0
        )
    )

    assert (
        probabilities.win
        == pytest.approx(
            probabilities.loss
        )
    )


def test_higher_expected_goals_improve_win_probability():

    lower = ResultProbabilityEvaluator.evaluate(
        expected_goals=1.5,
        opponent_expected_goals=1.5
    )

    higher = ResultProbabilityEvaluator.evaluate(
        expected_goals=2.5,
        opponent_expected_goals=1.5
    )

    assert higher.win > lower.win


def test_lower_opponent_expected_goals_reduce_loss_probability():

    higher_opponent_xg = (
        ResultProbabilityEvaluator.evaluate(
            expected_goals=1.5,
            opponent_expected_goals=2.5
        )
    )

    lower_opponent_xg = (
        ResultProbabilityEvaluator.evaluate(
            expected_goals=1.5,
            opponent_expected_goals=1.0
        )
    )

    assert (
        lower_opponent_xg.loss
        < higher_opponent_xg.loss
    )


def test_default_distribution_preserves_existing_behavior():

    team = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=45,
        left_attack=20,
        central_attack=30,
        right_attack=25
    )

    opponent = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=40,
        left_attack=20,
        central_attack=30,
        right_attack=25
    )

    default_result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    explicit_result = MatchEvaluator.evaluate(
        team,
        opponent,
        our_distribution=ChanceDistribution(
            left=0.25,
            center=0.50,
            right=0.25
        ),
        opponent_distribution=ChanceDistribution(
            left=0.25,
            center=0.50,
            right=0.25
        )
    )

    assert (
        default_result.expected_goals
        == pytest.approx(
            explicit_result.expected_goals
        )
    )

    assert (
        default_result.opponent_expected_goals
        == pytest.approx(
            explicit_result.opponent_expected_goals
        )
    )


def test_more_central_chances_help_strong_central_attack():

    team = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=45,
        left_attack=10,
        central_attack=50,
        right_attack=10
    )

    opponent = TeamRatings(
        left_defense=35,
        central_defense=15,
        right_defense=35,
        midfield=40,
        left_attack=25,
        central_attack=25,
        right_attack=25
    )

    normal_result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    central_result = MatchEvaluator.evaluate(
        team,
        opponent,
        our_distribution=ChanceDistribution(
            left=0.15,
            center=0.70,
            right=0.15
        )
    )

    assert (
        central_result.expected_goals
        > normal_result.expected_goals
    )


def test_more_wing_chances_help_strong_wing_attacks():

    team = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=45,
        left_attack=50,
        central_attack=10,
        right_attack=50
    )

    opponent = TeamRatings(
        left_defense=15,
        central_defense=45,
        right_defense=15,
        midfield=40,
        left_attack=25,
        central_attack=25,
        right_attack=25
    )

    normal_result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    wing_result = MatchEvaluator.evaluate(
        team,
        opponent,
        our_distribution=ChanceDistribution(
            left=0.40,
            center=0.20,
            right=0.40
        )
    )

    assert (
        wing_result.expected_goals
        > normal_result.expected_goals
    )


def test_our_distribution_does_not_change_opponent_xg():

    team = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=45,
        left_attack=50,
        central_attack=10,
        right_attack=50
    )

    opponent = TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=25,
        midfield=40,
        left_attack=25,
        central_attack=25,
        right_attack=25
    )

    normal_result = MatchEvaluator.evaluate(
        team,
        opponent
    )

    modified_result = MatchEvaluator.evaluate(
        team,
        opponent,
        our_distribution=ChanceDistribution(
            left=0.40,
            center=0.20,
            right=0.40
        )
    )

    assert (
        modified_result.opponent_expected_goals
        == pytest.approx(
            normal_result.opponent_expected_goals
        )
    )