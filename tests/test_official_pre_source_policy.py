from engine.history.models import SectorRatings
from engine.ratings.rating_source_policy import (
    SOURCE_INTERNAL_DIAGNOSTIC,
    SOURCE_OFFICIAL_PRE,
    select_our_ratings,
)
from engine.ratings.sector_rating import SOURCE_HATTRICK_DECIMAL, SOURCE_HT_COACH_INTERNAL
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    TeamRatingsResult,
)


def _internal_ratings():
    return TeamRatingsResult(
        left_defense=100, central_defense=120, right_defense=95, midfield=140,
        left_attack=110, central_attack=150, right_attack=105,
    )


def _opponent_ratings():
    return TeamRatingsResult(
        left_defense=6.0, central_defense=7.0, right_defense=5.5, midfield=6.5,
        left_attack=7.5, central_attack=8.0, right_attack=6.0,
    )


def _official_pre():
    return SectorRatings(
        left_defense=4.25, central_defense=7.0, right_defense=3.75, midfield=7.25,
        left_attack=7.75, central_attack=9.75, right_attack=8.0,
    )


def _service():
    return MatchWorkspaceService.__new__(MatchWorkspaceService)


def _recommended_formation(service):
    our = _internal_ratings()
    opponent = _opponent_ratings()
    return FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=our, opponent_ratings=opponent,
        sector_rating_comparisons=service._map_sector_comparisons(our, opponent),
    )


def test_official_pre_wins_when_present():
    selection = select_our_ratings(_internal_ratings(), _official_pre())
    assert selection.source == SOURCE_OFFICIAL_PRE
    assert selection.scale == SOURCE_HATTRICK_DECIMAL
    assert selection.is_official


def test_falls_back_to_internal_diagnostic_when_no_official_pre():
    selection = select_our_ratings(_internal_ratings(), None)
    assert selection.source == SOURCE_INTERNAL_DIAGNOSTIC
    assert selection.scale == SOURCE_HT_COACH_INTERNAL
    assert not selection.is_official


def test_empty_official_pre_falls_back_to_internal():
    selection = select_our_ratings(_internal_ratings(), SectorRatings())
    assert selection.source == SOURCE_INTERNAL_DIAGNOSTIC


def test_calibrated_internal_tier_never_fires_yet():
    from engine.ratings.rating_source_policy import CALIBRATED_INTERNAL_CONFIRMED

    assert CALIBRATED_INTERNAL_CONFIRMED is False


def test_override_preserves_comparable_recommended_formation():
    service = _service()
    formation = _recommended_formation(service)
    result = MatchAnalysisResult(player_count=18, opponent_name="Rival", formations=[formation])

    assert any(c.comparable for c in result.recommended_formation.sector_rating_comparisons)

    updated = service.apply_official_pre_override(result, _official_pre())
    comparisons = updated.recommended_formation.sector_rating_comparisons
    assert any(c.comparable for c in comparisons)


def test_override_uses_hattrick_scale_values_not_internal():
    service = _service()
    formation = _recommended_formation(service)
    result = MatchAnalysisResult(player_count=18, opponent_name="Rival", formations=[formation])

    updated = service.apply_official_pre_override(result, _official_pre())
    midfield = next(
        c for c in updated.recommended_formation.sector_rating_comparisons
        if c.matchup_key == "midfield"
    )
    assert midfield.our_value == 7.25


def test_override_does_not_mutate_other_formations():
    service = _service()
    recommended = _recommended_formation(service)
    other = FormationAnalysisResult(
        formation_name="3-4-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.4, draw_probability=0.3, loss_probability=0.3,
        possession=48.0, expected_goals=1.2, opponent_expected_goals=1.3,
        is_recommended=False, team_ratings=_internal_ratings(),
        opponent_ratings=_opponent_ratings(),
        sector_rating_comparisons=service._map_sector_comparisons(
            _internal_ratings(), _opponent_ratings()
        ),
    )
    result = MatchAnalysisResult(
        player_count=18, opponent_name="Rival", formations=[recommended, other]
    )

    updated = service.apply_official_pre_override(result, _official_pre())
    updated_other = next(f for f in updated.formations if f.formation_name == "3-4-3")
    assert updated_other.team_ratings == _internal_ratings()


def test_override_is_a_no_op_without_official_pre():
    service = _service()
    formation = _recommended_formation(service)
    result = MatchAnalysisResult(player_count=18, opponent_name="Rival", formations=[formation])

    updated = service.apply_official_pre_override(result, None)
    assert updated is result


def test_override_is_a_no_op_with_no_recommended_formation():
    service = _service()
    result = MatchAnalysisResult(player_count=18, opponent_name="Rival", formations=[])

    updated = service.apply_official_pre_override(result, _official_pre())
    assert updated is result


def test_override_handles_partial_official_pre_without_crashing():
    service = _service()
    formation = _recommended_formation(service)
    result = MatchAnalysisResult(player_count=18, opponent_name="Rival", formations=[formation])

    partial = SectorRatings(left_defense=4.25, midfield=7.25)
    updated = service.apply_official_pre_override(result, partial)
    assert updated.recommended_formation.team_ratings.left_defense == 4.25
    assert updated.recommended_formation.team_ratings.central_defense == 0.0


def test_map_team_ratings_handles_none_sector_without_crashing():
    service = _service()
    ratings = SectorRatings(left_defense=4.25, central_defense=None)
    mapped = service._map_team_ratings(ratings)
    assert mapped.left_defense == 4.25
    assert mapped.central_defense == 0.0
