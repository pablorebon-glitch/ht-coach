import unittest
from dataclasses import replace

from engine.advisor.recommendation import Recommendation
from engine.advisor.recommendation_engine import RecommendationEngine
from engine.advisor.recommendation_ranker import RecommendationRanker
from engine.advisor.recommendation_types import (
    RecommendationCategory,
    RecommendationConfidence,
)
from ht_coach_app.change_analysis.service import ChangeAnalysisService
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    TeamRatingsResult,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
    with_tactical_advisor,
)
from ht_coach_app.workspace.workspace_models import (
    WorkspaceModification,
    WorkspaceState,
)

try:
    from PySide6.QtWidgets import QApplication, QLabel
    from ht_coach_app.views.match_page import MatchPage
except Exception:
    QApplication = None
    QLabel = None
    MatchPage = None


def formation(
    name,
    win,
    possession=0.50,
    midfield=40,
    central_defense=42,
    left_attack=30,
    central_attack=31,
    right_attack=30,
    opponent_midfield=44,
    recommended=False,
):
    return FormationAnalysisResult(
        formation_name=name,
        recommended_tactic="NORMAL",
        tactic_level=5.0,
        win_probability=win,
        draw_probability=0.30,
        loss_probability=1.0 - win - 0.30,
        possession=possession,
        expected_goals=2.0,
        opponent_expected_goals=1.2,
        is_recommended=recommended,
        team_ratings=TeamRatingsResult(
            midfield=midfield,
            central_defense=central_defense,
            left_attack=left_attack,
            central_attack=central_attack,
            right_attack=right_attack,
        ),
        opponent_ratings=TeamRatingsResult(
            midfield=opponent_midfield,
            central_defense=36,
            left_attack=30,
            central_attack=30,
            right_attack=30,
        ),
    )


def match_result(*formations):
    return MatchAnalysisResult(
        player_count=20,
        opponent_name="Rival FC",
        analyzed_formations=[item.formation_name for item in formations],
        formations=list(formations),
    )


def workspace_state():
    return WorkspaceState(
        history=(
            WorkspaceModification(
                formation_name="3-5-2",
                slot_id="im-center-1",
                role="Inner Midfielder (IM)",
                original_player_name="Old Midfielder",
                replacement_player_name="New Midfielder",
                score_difference=1.1,
                previous_slot_score=7.2,
                current_slot_score=8.3,
            ),
        )
    )


class TacticalAdvisorEngineTest(unittest.TestCase):
    def test_recommendations_are_ranked_by_impact(self):
        result = match_result(
            formation("3-5-2", 0.40, midfield=34, recommended=True),
            formation("4-5-1", 0.415, midfield=42),
        )

        recommendations = RecommendationEngine().recommend(result)

        self.assertGreaterEqual(len(recommendations), 2)
        self.assertEqual(
            recommendations,
            sorted(
                recommendations,
                key=lambda item: (
                    item.impact_score,
                    item.estimated_win_delta,
                    item.code,
                ),
                reverse=True,
            ),
        )

    def test_formation_rule_respects_threshold(self):
        result = match_result(
            formation("3-5-2", 0.400, recommended=True),
            formation("4-5-1", 0.403),
        )

        codes = [
            recommendation.code
            for recommendation in RecommendationEngine().recommend(result)
        ]

        self.assertNotIn("formation:4-5-1", codes)

    def test_no_duplicate_recommendations_after_ranking(self):
        duplicate = Recommendation(
            code="same",
            title_key="advisor.title",
            explanation_key="advisor.empty",
            category=RecommendationCategory.BALANCE,
            impact_score=1.0,
            confidence=RecommendationConfidence.LOW,
        )
        stronger = replace(duplicate, impact_score=2.0)

        ranked = RecommendationRanker().rank([duplicate, stronger])

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].impact_score, 2.0)

    def test_lineup_rule_uses_change_analysis(self):
        previous = match_result(
            formation("3-5-2", 0.40, recommended=True)
        )
        current = match_result(
            formation("3-5-2", 0.414, recommended=True)
        )
        analysis = ChangeAnalysisService().analyze(
            previous,
            current,
            workspace_state(),
        )
        enriched = with_tactical_advisor(
            replace(current, change_analysis=analysis)
        )

        codes = [
            recommendation.code
            for recommendation in enriched.tactical_advisor
        ]

        self.assertIn("lineup:last_change", codes)

    def test_persistence_preserves_advisor_recommendations(self):
        result = with_tactical_advisor(
            match_result(
                formation("3-5-2", 0.40, recommended=True),
                formation("4-5-1", 0.42),
            )
        )

        restored = match_analysis_result_from_dict(
            match_analysis_result_to_dict(result)
        )

        self.assertTrue(restored.tactical_advisor)
        self.assertEqual(
            restored.tactical_advisor[0].code,
            result.tactical_advisor[0].code,
        )


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class TacticalAdvisorViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_match_page_renders_tactical_advisor(self):
        result = with_tactical_advisor(
            match_result(
                formation("3-5-2", 0.40, midfield=34, recommended=True),
                formation("4-5-1", 0.42, midfield=44),
            )
        )
        page = MatchPage()
        page.show_results(result)

        labels = [
            label.text()
            for label in page.findChildren(QLabel)
        ]

        self.assertIn("Tactical Advisor", labels)

    def test_simple_verbosity_hides_explanations(self):
        result = with_tactical_advisor(
            match_result(
                formation("3-5-2", 0.40, midfield=34, recommended=True),
                formation("4-5-1", 0.42, midfield=44),
            )
        )
        page = MatchPage()
        page.set_advisor_verbosity("simple")
        page.show_results(result)

        labels = [
            label.text()
            for label in page.findChildren(QLabel)
        ]

        self.assertNotIn(
            "This evaluated formation improves win probability by 2.0% "
            "without being weaker than the current recommendation.",
            labels,
        )
