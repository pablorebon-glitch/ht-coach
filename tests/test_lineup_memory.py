from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    TeamRatingsResult,
)
from engine.lineup_memory import (
    StabilityClassification,
    StabilityThresholds,
    classify_stability,
    compare_lineups,
    explain_revision,
    recommends_keeping_previous_lineup,
)


def _lineup(slot_names, formation="3-5-2"):
    players = []
    for number, name in enumerate(slot_names, start=1):
        players.append(
            LineupPlayerResult(
                number=number, position="INNER_MIDFIELDER", side="CENTER",
                order="Normal", order_side="", player_name=name,
            )
        )
    return players


def _formation(names, formation_name="3-5-2", tactic="Normal", win_probability=0.5,
               possession=50.0, expected_goals=1.5, team_ratings=None):
    return FormationAnalysisResult(
        formation_name=formation_name, recommended_tactic=tactic, tactic_level=5,
        win_probability=win_probability, draw_probability=0.3, loss_probability=0.2,
        possession=possession, expected_goals=expected_goals, opponent_expected_goals=1.2,
        team_ratings=team_ratings or TeamRatingsResult(),
        lineup=_lineup(names, formation_name),
    )


def test_no_previous_plan_produces_empty_comparison():
    new = _formation([f"P{i}" for i in range(1, 12)])
    revision = compare_lineups(None, new, match_record_id="m1")
    assert not revision.has_previous_plan
    assert revision.changed_slots == ()
    assert revision.possession_delta == 0.0


def test_identical_lineups_produce_no_changes():
    names = [f"P{i}" for i in range(1, 12)]
    previous = _formation(names)
    new = _formation(names)
    revision = compare_lineups(previous, new)
    assert revision.changed_slots == ()
    assert not revision.has_changes


def test_single_player_swap_is_detected():
    previous_names = [f"P{i}" for i in range(1, 12)]
    new_names = list(previous_names)
    new_names[3] = "Bassedas"
    previous_names_with_leaving = list(previous_names)
    previous_names_with_leaving[3] = "Alvarez"

    previous = _formation(previous_names_with_leaving)
    new = _formation(new_names)
    revision = compare_lineups(previous, new)

    assert len(revision.changed_slots) == 1
    assert "Bassedas" in revision.changed_players
    assert "Alvarez" in revision.changed_players


def test_order_only_change_is_tracked_separately_from_player_changes():
    names = [f"P{i}" for i in range(1, 12)]
    previous = _formation(names)
    new_lineup = _lineup(names)
    new_lineup[3] = LineupPlayerResult(
        number=4, position="INNER_MIDFIELDER", side="CENTER",
        order="Offensive", order_side="", player_name=names[3],
    )
    new = FormationAnalysisResult(
        formation_name="3-5-2", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        team_ratings=TeamRatingsResult(), lineup=tuple(new_lineup),
    )
    revision = compare_lineups(previous, new)
    assert len(revision.changed_orders) == 1
    assert revision.changed_players == ()


def test_formation_change_is_flagged_without_slot_by_slot_diff():
    previous = _formation([f"P{i}" for i in range(1, 12)], formation_name="3-5-2")
    new = _formation([f"P{i}" for i in range(1, 12)], formation_name="4-4-2")
    revision = compare_lineups(previous, new)
    assert revision.changed_formation is True
    assert revision.previous_formation == "3-5-2"
    assert revision.new_formation == "4-4-2"


def test_tactic_change_is_detected():
    previous = _formation([f"P{i}" for i in range(1, 12)], tactic="Normal")
    new = _formation([f"P{i}" for i in range(1, 12)], tactic="Pressing")
    revision = compare_lineups(previous, new)
    assert revision.changed_tactic is True


def test_sector_deltas_reflect_exact_rating_differences():
    previous = _formation(
        [f"P{i}" for i in range(1, 12)],
        team_ratings=TeamRatingsResult(midfield=7.0, central_defense=7.0),
    )
    new = _formation(
        [f"P{i}" for i in range(1, 12)],
        team_ratings=TeamRatingsResult(midfield=7.3, central_defense=6.8),
    )
    revision = compare_lineups(previous, new)
    deltas = {d.sector: d.delta for d in revision.sector_deltas}
    assert deltas["midfield"] == 0.3
    assert deltas["central_defense"] == -0.2


def test_possession_xg_and_win_probability_deltas_are_signed():
    previous = _formation([f"P{i}" for i in range(1, 12)], win_probability=0.45, possession=48.0, expected_goals=1.3)
    new = _formation([f"P{i}" for i in range(1, 12)], win_probability=0.50, possession=52.0, expected_goals=1.5)
    revision = compare_lineups(previous, new)
    assert revision.win_probability_delta == 0.05
    assert revision.possession_delta == 4.0
    assert round(revision.xg_delta, 2) == 0.2


def test_no_previous_plan_is_equivalent():
    new = _formation([f"P{i}" for i in range(1, 12)])
    revision = compare_lineups(None, new)
    assert classify_stability(revision) == StabilityClassification.EQUIVALENT


def test_no_changes_is_equivalent():
    names = [f"P{i}" for i in range(1, 12)]
    revision = compare_lineups(_formation(names), _formation(names))
    assert classify_stability(revision) == StabilityClassification.EQUIVALENT


def test_marginal_win_probability_change_is_marginal():
    prev_names = [f"P{i}" for i in range(1, 12)]
    prev_names[3] = "Alvarez"
    new_names = [f"P{i}" for i in range(1, 12)]
    new_names[3] = "Bassedas"
    previous = _formation(prev_names, win_probability=0.500)
    new = _formation(new_names, win_probability=0.508)
    revision = compare_lineups(previous, new)
    assert classify_stability(revision) == StabilityClassification.MARGINAL_CHANGE


def test_clear_win_probability_improvement_is_clear_improvement():
    prev_names = [f"P{i}" for i in range(1, 12)]
    prev_names[3] = "Alvarez"
    new_names = [f"P{i}" for i in range(1, 12)]
    new_names[3] = "Bassedas"
    previous = _formation(prev_names, win_probability=0.45)
    new = _formation(new_names, win_probability=0.55)
    revision = compare_lineups(previous, new)
    assert classify_stability(revision) == StabilityClassification.CLEAR_IMPROVEMENT


def test_trade_off_when_sectors_move_in_opposite_directions():
    prev_names = [f"P{i}" for i in range(1, 12)]
    prev_names[3] = "Alvarez"
    new_names = [f"P{i}" for i in range(1, 12)]
    new_names[3] = "Bassedas"
    previous = _formation(
        prev_names, win_probability=0.50,
        team_ratings=TeamRatingsResult(midfield=7.0, central_defense=7.0),
    )
    new = _formation(
        new_names, win_probability=0.505,
        team_ratings=TeamRatingsResult(midfield=7.3, central_defense=6.8),
    )
    revision = compare_lineups(previous, new)
    assert classify_stability(revision) == StabilityClassification.TRADE_OFF


def test_custom_thresholds_change_classification():
    prev_names = [f"P{i}" for i in range(1, 12)]
    prev_names[3] = "Alvarez"
    new_names = [f"P{i}" for i in range(1, 12)]
    new_names[3] = "Bassedas"
    previous = _formation(prev_names, win_probability=0.50)
    new = _formation(new_names, win_probability=0.503)
    revision = compare_lineups(previous, new)

    lenient = StabilityThresholds(marginal_win_probability_delta=0.01)
    assert classify_stability(revision, lenient) == StabilityClassification.EQUIVALENT


def test_recommends_keeping_previous_for_equivalent_and_marginal():
    assert recommends_keeping_previous_lineup(StabilityClassification.EQUIVALENT)
    assert recommends_keeping_previous_lineup(StabilityClassification.MARGINAL_CHANGE)
    assert not recommends_keeping_previous_lineup(StabilityClassification.CLEAR_IMPROVEMENT)


def test_briefs_own_worked_example_bassedas_vs_alvarez():
    prev_names = [f"P{i}" for i in range(1, 12)]
    prev_names[3] = "Feliciano Alvarez"
    new_names = [f"P{i}" for i in range(1, 12)]
    new_names[3] = "Mauricio Bassedas"
    previous = _formation(
        prev_names, win_probability=0.50,
        team_ratings=TeamRatingsResult(midfield=7.0, central_defense=7.0),
    )
    new = _formation(
        new_names, win_probability=0.505,
        team_ratings=TeamRatingsResult(midfield=7.3, central_defense=6.8),
    )
    revision = compare_lineups(previous, new)
    classification = classify_stability(revision)
    explanation = explain_revision(revision, classification)

    assert len(explanation.slot_explanations) == 1
    slot_explanation = explanation.slot_explanations[0]
    assert slot_explanation.entering_player == "Mauricio Bassedas"
    assert slot_explanation.leaving_player == "Feliciano Alvarez"
    assert slot_explanation.objective_params["sector"] == "midfield"
    assert slot_explanation.weakens_params["sector"] == "central_defense"
    assert slot_explanation.is_significant_tradeoff is True


def test_explanation_never_invents_a_cause_without_evidence():
    prev_names = [f"P{i}" for i in range(1, 12)]
    prev_names[3] = "Alvarez"
    new_names = [f"P{i}" for i in range(1, 12)]
    new_names[3] = "Bassedas"
    previous = _formation(prev_names, team_ratings=TeamRatingsResult(midfield=7.0))
    new = _formation(new_names, team_ratings=TeamRatingsResult(midfield=7.02))
    revision = compare_lineups(previous, new)
    classification = classify_stability(revision)
    explanation = explain_revision(revision, classification)

    slot_explanation = explanation.slot_explanations[0]
    assert slot_explanation.objective_key == "match_decision.objective.no_clear_gain"
    assert slot_explanation.weakens_key == "match_decision.weakens.none"


def test_equivalent_classification_recommends_keeping_previous():
    names = [f"P{i}" for i in range(1, 12)]
    revision = compare_lineups(_formation(names), _formation(names))
    classification = classify_stability(revision)
    explanation = explain_revision(revision, classification)
    assert explanation.keep_previous_reasonable is True
    assert explanation.recommendation_key == "match_decision.recommendation.equivalent"


def test_no_previous_plan_explanation_is_distinct():
    new = _formation([f"P{i}" for i in range(1, 12)])
    revision = compare_lineups(None, new)
    classification = classify_stability(revision)
    explanation = explain_revision(revision, classification)
    assert explanation.recommendation_key == "match_decision.recommendation.no_previous_plan"


def test_explanation_to_dict_is_serializable():
    prev_names = [f"P{i}" for i in range(1, 12)]
    prev_names[3] = "Alvarez"
    new_names = [f"P{i}" for i in range(1, 12)]
    new_names[3] = "Bassedas"
    previous = _formation(prev_names)
    new = _formation(new_names)
    revision = compare_lineups(previous, new)
    classification = classify_stability(revision)
    explanation = explain_revision(revision, classification)
    payload = explanation.to_dict()
    assert isinstance(payload["slot_explanations"], list)
    assert payload["significance"] == classification.value
