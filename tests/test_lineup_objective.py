import pytest

from engine.optimizers.lineup_objective import (
    HeadToHeadLineupComparator,
    LineupObjectiveEvaluator,
    TACTICAL_TIE_TOLERANCE,
)
from models.team_ratings import TeamRatings
from models.tactic import Tactic


def la_rocha_opponent():
    return TeamRatings(
        left_defense=8.50,
        central_defense=13.00,
        right_defense=7.50,
        midfield=5.75,
        left_attack=4.00,
        central_attack=7.00,
        right_attack=4.25,
    )


def la_rocha_candidate_a():
    return TeamRatings(
        left_defense=4.25,
        central_defense=5.25,
        right_defense=4.25,
        midfield=6.75,
        left_attack=9.50,
        central_attack=12.50,
        right_attack=9.25,
    )


def la_rocha_candidate_b():
    return TeamRatings(
        left_defense=4.25,
        central_defense=5.25,
        right_defense=4.50,
        midfield=7.75,
        left_attack=9.25,
        central_attack=12.25,
        right_attack=9.00,
    )


def compare(a=None, b=None, opponent=None, tactic=Tactic.ATTACK_ON_WINGS):
    return HeadToHeadLineupComparator().compare(
        a or la_rocha_candidate_a(),
        b or la_rocha_candidate_b(),
        opponent or la_rocha_opponent(),
        tactic=tactic,
        training_score_a=0.0,
        training_score_b=0.0,
    )


def test_la_rocha_fixture_prefers_bassedas_variant_by_tactical_value():
    result = compare()

    assert result.preferred_candidate_id == "B"
    assert result.training_impact == pytest.approx(0.0)
    assert result.candidate_b.components.win_probability > (
        result.candidate_a.components.win_probability
    )
    assert result.expected_scoring_impact > 0
    assert result.expected_concession_impact < 0
    assert "mediocampo" in result.summary


def test_la_rocha_fixture_explanation_references_calculated_deltas():
    result = compare()

    midfield = next(
        delta for delta in result.sector_deltas
        if delta.sector == "midfield"
    )
    right_defense = next(
        delta for delta in result.sector_deltas
        if delta.sector == "right_defense"
    )

    assert midfield.value == pytest.approx(1.0)
    assert right_defense.value == pytest.approx(0.25)
    assert "+1.00 HT" in result.explanation
    assert "xG rival" in result.explanation


def test_objective_trace_contains_required_debug_components():
    trace = LineupObjectiveEvaluator.evaluate_ratings(
        la_rocha_candidate_b(),
        la_rocha_opponent(),
        tactic=Tactic.ATTACK_ON_WINGS,
        candidate_id="bassedas-variant",
    )

    assert trace.candidate_id == "bassedas-variant"
    assert trace.sector_ratings["midfield"] == pytest.approx(7.75)
    assert trace.components.lineup_positional_score > 0
    assert trace.components.possession_component > 0
    assert trace.components.attack_matchup_component == pytest.approx(
        trace.components.expected_goals
    )
    assert trace.components.final_objective_score == pytest.approx(
        trace.components.win_probability
    )


def test_possession_gain_receives_contextual_value():
    base = TeamRatings(
        left_defense=8,
        central_defense=8,
        right_defense=8,
        midfield=5,
        left_attack=8,
        central_attack=8,
        right_attack=8,
    )
    plus_midfield = TeamRatings(
        left_defense=8,
        central_defense=8,
        right_defense=8,
        midfield=6,
        left_attack=8,
        central_attack=8,
        right_attack=8,
    )
    weak_midfield = TeamRatings(
        left_defense=8,
        central_defense=8,
        right_defense=8,
        midfield=2,
        left_attack=8,
        central_attack=8,
        right_attack=8,
    )
    contested_midfield = TeamRatings(
        left_defense=8,
        central_defense=8,
        right_defense=8,
        midfield=5,
        left_attack=8,
        central_attack=8,
        right_attack=8,
    )

    weak = compare(base, plus_midfield, weak_midfield, Tactic.NORMAL)
    contested = compare(base, plus_midfield, contested_midfield, Tactic.NORMAL)

    assert contested.possession_delta > weak.possession_delta
    assert contested.expected_scoring_impact > weak.expected_scoring_impact


def test_aow_reduces_central_route_weight_and_values_wings():
    normal = LineupObjectiveEvaluator.evaluate_ratings(
        la_rocha_candidate_a(),
        la_rocha_opponent(),
        tactic=Tactic.NORMAL,
    )
    aow = LineupObjectiveEvaluator.evaluate_ratings(
        la_rocha_candidate_a(),
        la_rocha_opponent(),
        tactic=Tactic.ATTACK_ON_WINGS,
    )

    assert aow.route_weights["center"] < normal.route_weights["center"]
    assert aow.route_weights["left"] > normal.route_weights["left"]
    assert aow.route_weights["right"] > normal.route_weights["right"]


def test_training_breaks_tactical_tie_only_when_close():
    a = TeamRatings(midfield=8, left_attack=8, central_attack=8, right_attack=8)
    b = TeamRatings(midfield=8, left_attack=8, central_attack=8, right_attack=8)
    opponent = TeamRatings(
        midfield=8,
        left_defense=8,
        central_defense=8,
        right_defense=8,
    )

    result = HeadToHeadLineupComparator().compare(
        a,
        b,
        opponent,
        training_score_a=0.0,
        training_score_b=1.0,
    )

    assert result.preferred_candidate_id == "B"
    assert "training tiebreaker" in result.final_tactical_preference


def test_training_does_not_override_clear_tactical_loss():
    result = HeadToHeadLineupComparator().compare(
        la_rocha_candidate_b(),
        la_rocha_candidate_a(),
        la_rocha_opponent(),
        tactic=Tactic.ATTACK_ON_WINGS,
        training_score_a=0.0,
        training_score_b=100.0,
    )

    tactical_gap = (
        result.candidate_a.components.win_probability
        - result.candidate_b.components.win_probability
    )
    assert tactical_gap > TACTICAL_TIE_TOLERANCE
    assert result.preferred_candidate_id == "A"


def test_context_can_make_defense_more_valuable_than_midfield():
    base = TeamRatings(
        left_defense=3,
        central_defense=3,
        right_defense=3,
        midfield=8,
        left_attack=7,
        central_attack=7,
        right_attack=7,
    )
    midfield_variant = TeamRatings(
        left_defense=3,
        central_defense=3,
        right_defense=3,
        midfield=8.25,
        left_attack=7,
        central_attack=7,
        right_attack=7,
    )
    defense_variant = TeamRatings(
        left_defense=3,
        central_defense=13,
        right_defense=3,
        midfield=8,
        left_attack=7,
        central_attack=7,
        right_attack=7,
    )
    opponent = TeamRatings(
        left_defense=7,
        central_defense=7,
        right_defense=7,
        midfield=1,
        left_attack=6,
        central_attack=12,
        right_attack=6,
    )

    midfield = compare(base, midfield_variant, opponent, Tactic.NORMAL)
    defense = compare(base, defense_variant, opponent, Tactic.NORMAL)

    assert abs(defense.expected_concession_impact) > abs(
        midfield.expected_concession_impact
    )
    assert defense.candidate_b.components.win_probability > (
        midfield.candidate_b.components.win_probability
    )
