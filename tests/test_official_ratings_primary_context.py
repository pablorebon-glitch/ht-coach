import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.models import SectorRatings
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    SectorRatingComparisonResult,
    TeamRatingsResult,
)
from ht_coach_app.views.match_page import MatchPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])


def _service():
    return MatchWorkspaceService.__new__(MatchWorkspaceService)


def _formation_with_comparisons():
    service = _service()
    our = TeamRatingsResult(
        left_defense=100, central_defense=120, right_defense=95, midfield=140,
        left_attack=110, central_attack=150, right_attack=105,
    )
    opponent = TeamRatingsResult(
        left_defense=6.0, central_defense=7.0, right_defense=5.5, midfield=6.5,
        left_attack=7.5, central_attack=8.0, right_attack=6.0,
    )
    return FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=our, opponent_ratings=opponent,
        sector_rating_comparisons=service._map_sector_comparisons(our, opponent),
    )


def _official_pre():
    return SectorRatings(
        left_defense=4.25, central_defense=7.0, right_defense=3.75, midfield=7.25,
        left_attack=7.75, central_attack=9.75, right_attack=8.0,
    )


def test_missing_indirect_set_piece_data_does_not_block_comparability():
    service = _service()
    formation = _formation_with_comparisons()
    result = MatchAnalysisResult(player_count=18, opponent_name="Rival", formations=[formation])

    updated = service.apply_official_pre_override(result, _official_pre())

    indirect = [
        c for c in updated.recommended_formation.sector_rating_comparisons
        if c.matchup_key in ("indirect_defense", "indirect_attack")
    ]
    assert indirect and all(not c.comparable for c in indirect)

    page = MatchPage()
    assert page._sector_ratings_comparable(updated.recommended_formation) is True


def test_genuine_scale_mismatch_still_reported():
    formation = _formation_with_comparisons()
    formation = FormationAnalysisResult(
        **{
            **formation.__dict__,
            "sector_rating_comparisons": [
                SectorRatingComparisonResult(
                    matchup_key="midfield",
                    our_sector="midfield",
                    opponent_sector="midfield",
                    our_value=140,
                    opponent_value=6.5,
                    our_scale="ht_coach_internal_contribution",
                    opponent_scale="hattrick_decimal",
                    difference=None,
                    advantage="not_directly_comparable",
                    comparable=False,
                )
            ],
        }
    )
    page = MatchPage()
    assert page._sector_ratings_comparable(formation) is False


def test_no_comparisons_at_all_defaults_to_comparable():
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
    )
    page = MatchPage()
    assert page._sector_ratings_comparable(formation) is True


def test_matchup_matrix_no_longer_duplicated_in_main_panel():
    """Alpha 0.6.6, Part 6: the raw matchup matrix table must live only
    in the technical/diagnostic section (_build_sector_rating_panel),
    never repeated inside the main Match Intelligence narrative
    panel."""
    from engine.match_intelligence.models import (
        MatchIntelligenceResult,
        MatchupInsight,
        MatchupMatrix,
        TeamProfile,
    )

    page = MatchPage()
    calls = []
    original = page._build_matchup_matrix
    page._build_matchup_matrix = lambda *args, **kwargs: calls.append("called") or original(*args, **kwargs)

    matrix = MatchupMatrix(
        our_attack_rows=(
            MatchupInsight(
                code="left_attack_vs_right_defense",
                perspective="our_attack",
                attack_sector="left_attack", defense_sector="right_defense",
                attack_value=8.0, defense_value=6.0,
                difference=1.0, classification="ADVANTAGE", advantage="ours",
                interpretation_key="match_intelligence.interpretation.advantage",
                is_best_route=True, is_worst_route=False,
            ),
        ),
        opponent_attack_rows=(),
    )
    intelligence = MatchIntelligenceResult(
        formation_name="3-5-2",
        our_profile=TeamProfile("midfield", "left_attack", "defense", "attack"),
        opponent_profile=TeamProfile("midfield", "left_attack", "defense", "attack"),
        matrix=matrix,
    )
    formation = _formation_with_comparisons()

    # main panel must NOT invoke the matrix builder
    page._build_match_intelligence_panel(intelligence, formation)
    assert calls == []

    # the technical/diagnostic panel is the one that shows it
    page._build_sector_rating_panel(formation, intelligence)
    assert calls == ["called"]
