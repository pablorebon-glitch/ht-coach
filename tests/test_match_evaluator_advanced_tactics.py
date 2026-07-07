import pytest

from engine.evaluators.match_evaluator import (
    MatchEvaluator
)

from models.team_ratings import TeamRatings


def make_team():

    return TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=45,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )


def make_opponent():

    return TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=40,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )


def test_pressing_reduces_total_expected_chances():

    team = make_team()

    opponent = make_opponent()

    normal = MatchEvaluator.evaluate(
        team,
        opponent
    )

    pressing = MatchEvaluator.evaluate(
        team,
        opponent,
        our_chance_multiplier=0.80,
        opponent_chance_multiplier=0.80
    )

    normal_total = (
        normal.expected_chances
        + normal.opponent_expected_chances
    )

    pressing_total = (
        pressing.expected_chances
        + pressing.opponent_expected_chances
    )

    assert pressing_total < normal_total


def test_counter_attacks_add_expected_chances():

    team = make_team()

    opponent = make_opponent()

    normal = MatchEvaluator.evaluate(
        team,
        opponent
    )

    counter_attacks = MatchEvaluator.evaluate(
        team,
        opponent,
        counter_attack_chances=1.5
    )

    assert (
        counter_attacks.expected_chances
        > normal.expected_chances
    )

    assert (
        counter_attacks.expected_goals
        > normal.expected_goals
    )


def test_play_creatively_adds_special_event_chances():

    team = make_team()

    opponent = make_opponent()

    normal = MatchEvaluator.evaluate(
        team,
        opponent
    )

    creative = MatchEvaluator.evaluate(
        team,
        opponent,
        special_event_multiplier=1.50
    )

    assert (
        creative.expected_chances
        > normal.expected_chances
    )


def test_play_creatively_improves_expected_goals():

    team = make_team()

    opponent = make_opponent()

    normal = MatchEvaluator.evaluate(
        team,
        opponent
    )

    creative = MatchEvaluator.evaluate(
        team,
        opponent,
        special_event_multiplier=1.50
    )

    assert (
        creative.expected_goals
        > normal.expected_goals
    )


def test_play_creatively_does_not_change_opponent_xg():

    team = make_team()

    opponent = make_opponent()

    normal = MatchEvaluator.evaluate(
        team,
        opponent
    )

    creative = MatchEvaluator.evaluate(
        team,
        opponent,
        special_event_multiplier=1.50
    )

    assert (
        creative.opponent_expected_goals
        == pytest.approx(
            normal.opponent_expected_goals
        )
    )


def test_play_creatively_is_neutral_at_multiplier_one():

    team = make_team()

    opponent = make_opponent()

    normal = MatchEvaluator.evaluate(
        team,
        opponent
    )

    creative = MatchEvaluator.evaluate(
        team,
        opponent,
        special_event_multiplier=1.0
    )

    assert (
        creative.expected_chances
        == pytest.approx(
            normal.expected_chances
        )
    )

    assert (
        creative.expected_goals
        == pytest.approx(
            normal.expected_goals
        )
    )


def test_higher_creativity_multiplier_produces_more_special_events():

    team = make_team()

    opponent = make_opponent()

    low_creativity = MatchEvaluator.evaluate(
        team,
        opponent,
        special_event_multiplier=1.10
    )

    high_creativity = MatchEvaluator.evaluate(
        team,
        opponent,
        special_event_multiplier=1.50
    )

    assert (
        high_creativity.expected_chances
        > low_creativity.expected_chances
    )

    assert (
        high_creativity.expected_goals
        > low_creativity.expected_goals
    )


def test_long_shots_changes_expected_goals():

    team = make_team()

    opponent = TeamRatings(
        left_defense=70,
        central_defense=70,
        right_defense=70,
        midfield=40,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    normal = MatchEvaluator.evaluate(
        team,
        opponent
    )

    long_shots = MatchEvaluator.evaluate(
        team,
        opponent,
        long_shot_conversion_rate=0.20
    )

    assert (
        long_shots.expected_goals
        != pytest.approx(
            normal.expected_goals
        )
    )