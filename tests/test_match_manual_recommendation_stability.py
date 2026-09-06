from types import SimpleNamespace

from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
)


def _formation(name, win, recommended=False):
    return FormationAnalysisResult(
        formation_name=name,
        recommended_tactic="Normal",
        tactic_level=0.0,
        win_probability=win,
        draw_probability=0.0,
        loss_probability=0.0,
        possession=0.0,
        expected_goals=0.0,
        opponent_expected_goals=0.0,
        is_recommended=recommended,
        lineup=[
            LineupPlayerResult(
                number=1,
                position="FORWARD",
                side="CENTER",
                order="NORMAL",
                order_side="",
                player_name=f"{name} Player",
            )
        ],
    )


def _result(formations, recommendation_revision=0, manual_lineup_revision=0):
    recommendation_id = next(
        (
            formation.formation_name
            for formation in formations
            if formation.is_recommended
        ),
        "",
    )
    return MatchAnalysisResult(
        player_count=11,
        opponent_name="PueblitoFC",
        formations=list(formations),
        recommendation_id=recommendation_id,
        recommendation_revision=recommendation_revision,
        manual_lineup_revision=manual_lineup_revision,
    )


def test_manual_workspace_reevaluation_preserves_previous_recommendation():
    previous = _result(
        [
            _formation("2-5-3", 0.51, recommended=True),
            _formation("3-5-2", 0.49),
        ],
        recommendation_revision=3,
        manual_lineup_revision=4,
    )
    reevaluated = _result(
        [
            _formation("3-5-2", 0.56, recommended=True),
            _formation("2-5-3", 0.52),
        ],
        recommendation_revision=0,
        manual_lineup_revision=0,
    )

    stable = MatchController._preserve_recommendation_after_manual_reevaluation(
        previous,
        reevaluated,
    )

    assert stable.recommended_formation.formation_name == "2-5-3"
    assert stable.recommendation_revision == 3
    assert stable.manual_lineup_revision == 5
    assert [item.is_recommended for item in stable.formations] == [False, True]
    assert stable.recommendation_id == "2-5-3"


def test_explicit_reoptimization_advances_recommendation_revision_only():
    previous = _result(
        [_formation("2-5-3", 0.51, recommended=True)],
        recommendation_revision=3,
        manual_lineup_revision=4,
    )
    optimized = _result(
        [_formation("3-5-2", 0.56, recommended=True)],
        recommendation_revision=0,
        manual_lineup_revision=0,
    )

    marked = MatchController._mark_explicit_recommendation_revision(
        previous,
        optimized,
    )

    assert marked.recommended_formation.formation_name == "3-5-2"
    assert marked.recommendation_id == "3-5-2"
    assert marked.recommendation_revision == 4
    assert marked.manual_lineup_revision == 4


def test_recommendation_identity_overrides_sorted_index_and_flags():
    result = MatchAnalysisResult(
        player_count=11,
        opponent_name="PueblitoFC",
        formations=[
            _formation("3-5-2", 0.60, recommended=True),
            _formation("2-5-3", 0.50),
        ],
        recommendation_id="2-5-3",
        recommendation_revision=7,
        manual_lineup_revision=3,
    )

    assert result.recommended_formation.formation_name == "2-5-3"


def test_recommendation_identity_survives_result_persistence_roundtrip():
    result = MatchAnalysisResult(
        player_count=11,
        opponent_name="PueblitoFC",
        formations=[
            _formation("3-5-2", 0.60, recommended=True),
            _formation("2-5-3", 0.50),
        ],
        recommendation_id="2-5-3",
        recommendation_revision=7,
        manual_lineup_revision=3,
    )

    restored = match_analysis_result_from_dict(match_analysis_result_to_dict(result))

    assert restored.recommendation_id == "2-5-3"
    assert restored.recommended_formation.formation_name == "2-5-3"


def test_visible_workspace_lineup_does_not_promote_alternative_recommendation():
    controller = MatchController.__new__(MatchController)
    controller._view = SimpleNamespace(
        tactic=lambda: "Normal",
        current_workspace_state=lambda: SimpleNamespace(
            current_board=SimpleNamespace(
                formation_name="3-5-2",
                tactic_level=0.0,
                slots=(
                    SimpleNamespace(
                        side="CENTER",
                        player=SimpleNamespace(
                            position="FORWARD",
                            side="CENTER",
                            individual_order="NORMAL",
                            order_side="",
                            player_name="Manual Player",
                        ),
                    ),
                ),
            )
        ),
    )
    result = MatchAnalysisResult(
        player_count=11,
        opponent_name="PueblitoFC",
        formations=[
            _formation("2-5-3", 0.51, recommended=True),
            _formation("3-5-2", 0.60),
        ],
        recommendation_id="2-5-3",
        recommendation_revision=4,
        manual_lineup_revision=2,
    )

    updated = controller._result_with_active_workspace_lineup(result)

    assert updated.recommendation_id == "2-5-3"
    assert updated.recommended_formation.formation_name == "2-5-3"
    assert [item.is_recommended for item in updated.formations] == [True, False]
    alternative = next(
        formation for formation in updated.formations
        if formation.formation_name == "3-5-2"
    )
    assert alternative.lineup[0].player_name == "Manual Player"


def test_runtime_guard_flags_non_explicit_recommendation_transition():
    events = []
    controller = MatchController.__new__(MatchController)
    controller._runtime_trace = SimpleNamespace(
        emit=lambda event_name, **payload: events.append((event_name, payload))
    )
    controller._last_traced_board_formation = "2-5-3"
    controller._last_traced_recommended_formation = "2-5-3"

    controller._trace_runtime_transitions(
        "FORMATION_BOARD_REBUILT",
        {
            "reason": "workspace_recalculation",
            "board_formation": "2-5-3",
            "recommended_formation": "3-5-2",
            "recommendation_revision": 4,
            "manual_lineup_revision": 5,
        },
    )

    assert any(
        event_name == "ILLEGAL_RECOMMENDATION_MUTATION"
        for event_name, _payload in events
    )


def test_runtime_guard_allows_explicit_optimizer_transition():
    events = []
    controller = MatchController.__new__(MatchController)
    controller._runtime_trace = SimpleNamespace(
        emit=lambda event_name, **payload: events.append((event_name, payload))
    )
    controller._last_traced_board_formation = "2-5-3"
    controller._last_traced_recommended_formation = "2-5-3"

    controller._trace_runtime_transitions(
        "ANALYSIS_RESULT_RECEIVED",
        {
            "reason": "primary_analysis",
            "board_formation": "3-5-2",
            "recommended_formation": "3-5-2",
            "recommendation_revision": 5,
            "manual_lineup_revision": 5,
        },
    )

    assert not any(
        event_name == "ILLEGAL_RECOMMENDATION_MUTATION"
        for event_name, _payload in events
    )
