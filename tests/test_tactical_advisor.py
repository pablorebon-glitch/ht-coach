import unittest
from dataclasses import replace

from engine.advisor.matchups import (
    opposing_defense_for_own_attack,
    own_defense_for_opponent_attack,
)
from engine.advisor.recommendation import Recommendation
from engine.advisor.recommendation_engine import (
    ACTIONABLE_WIN_DELTA,
    RecommendationEngine,
    format_win_delta,
    impact_band,
)
from engine.advisor.recommendation_ranker import RecommendationRanker
from engine.advisor.recommendation_types import (
    RecommendationCardType,
    RecommendationCategory,
    RecommendationConfidence,
)
from ht_coach_app.change_analysis.models import (
    ChangeAnalysisResult,
    ChangeValueDelta,
    LastChange,
    PositionFitChange,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    TeamRatingsResult,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
    with_tactical_advisor,
)

try:
    from PySide6.QtWidgets import QApplication, QLabel
    from ht_coach_app.views.match_page import MatchPage
except Exception:
    QApplication = None
    QLabel = None
    MatchPage = None


def ratings(
    midfield=40,
    left_defense=42,
    central_defense=42,
    right_defense=42,
    left_attack=30,
    central_attack=31,
    right_attack=30,
):
    return TeamRatingsResult(
        left_defense=left_defense,
        central_defense=central_defense,
        right_defense=right_defense,
        midfield=midfield,
        left_attack=left_attack,
        central_attack=central_attack,
        right_attack=right_attack,
    )


def formation(
    name,
    win,
    possession=0.50,
    recommended=False,
    team_ratings=None,
    opponent_ratings=None,
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
        team_ratings=team_ratings or ratings(),
        opponent_ratings=opponent_ratings or ratings(
            midfield=44,
            left_defense=36,
            central_defense=36,
            right_defense=36,
            left_attack=30,
            central_attack=30,
            right_attack=30,
        ),
    )


def match_result(*formations, change_analysis=None):
    return MatchAnalysisResult(
        player_count=20,
        opponent_name="Rival FC",
        analyzed_formations=[item.formation_name for item in formations],
        formations=list(formations),
        change_analysis=change_analysis,
    )


def lineup_change(win_delta):
    return ChangeAnalysisResult(
        last_change=LastChange(
            incoming_player="New Midfielder",
            outgoing_player="Old Midfielder",
            slot="Inner Midfielder (IM)",
            formation_name="3-5-2",
        ),
        position_fit=PositionFitChange(
            previous_player_score=7.2,
            current_player_score=8.3,
            difference=1.1,
        ),
        team_impact=[
            ChangeValueDelta("Win", 0.40, 0.40 + win_delta, win_delta),
        ],
        sector_changes=[
            ChangeValueDelta("midfield", 40, 42, 2),
        ],
    )


def advisor_codes(result):
    return [
        recommendation.code
        for recommendation in RecommendationEngine().recommend(result)
    ]


class TacticalAdvisorEngineTest(unittest.TestCase):
    def test_centralized_own_attack_matchups(self):
        self.assertEqual(
            opposing_defense_for_own_attack("left_attack"),
            "right_defense",
        )
        self.assertEqual(
            opposing_defense_for_own_attack("central_attack"),
            "central_defense",
        )
        self.assertEqual(
            opposing_defense_for_own_attack("right_attack"),
            "left_defense",
        )

    def test_centralized_opponent_attack_matchups(self):
        self.assertEqual(
            own_defense_for_opponent_attack("left_attack"),
            "right_defense",
        )
        self.assertEqual(
            own_defense_for_opponent_attack("central_attack"),
            "central_defense",
        )
        self.assertEqual(
            own_defense_for_opponent_attack("right_attack"),
            "left_defense",
        )

    def test_formation_action_requires_measurable_win_delta(self):
        result = match_result(
            formation("3-5-2", 0.400, recommended=True),
            formation("4-5-1", 0.400 + ACTIONABLE_WIN_DELTA / 2),
        )

        self.assertNotIn("formation:4-5-1", advisor_codes(result))

    def test_formation_action_contains_before_after_and_delta(self):
        result = match_result(
            formation(
                "3-5-2",
                0.400,
                recommended=True,
                team_ratings=ratings(midfield=38),
            ),
            formation(
                "4-5-1",
                0.418,
                team_ratings=ratings(midfield=42),
            ),
        )

        recommendations = RecommendationEngine().recommend(result)
        action = next(item for item in recommendations if item.is_action)

        self.assertEqual(action.card_type, RecommendationCardType.ACTION)
        self.assertEqual(action.title_key, "advisor.rule.use_formation.title")
        self.assertEqual(action.params["current_formation"], "3-5-2")
        self.assertEqual(action.params["formation"], "4-5-1")
        self.assertAlmostEqual(action.estimated_win_delta, 0.018)
        self.assertTrue(action.sector_deltas)

    def test_attack_matchup_uses_opposing_defense_not_opponent_attack(self):
        result = match_result(
            formation(
                "3-5-2",
                0.42,
                recommended=True,
                team_ratings=ratings(left_attack=25, central_attack=36, right_attack=34),
                opponent_ratings=ratings(
                    left_defense=28,
                    central_defense=35,
                    right_defense=40,
                    left_attack=10,
                    central_attack=10,
                    right_attack=10,
                ),
            )
        )

        codes = advisor_codes(result)

        self.assertIn("attack_matchup:left_attack->right_defense", codes)
        self.assertNotIn("attack_matchup:left_attack->left_attack", codes)

    def test_weak_attack_is_observation_not_strengthen_action(self):
        result = match_result(
            formation(
                "3-5-2",
                0.42,
                recommended=True,
                team_ratings=ratings(left_attack=20, central_attack=31, right_attack=30),
                opponent_ratings=ratings(
                    right_defense=36,
                    left_attack=10,
                    central_attack=10,
                    right_attack=10,
                ),
            )
        )

        recommendations = RecommendationEngine().recommend(result)
        attack = next(
            item for item in recommendations
            if item.code.startswith("attack_matchup:left_attack")
        )

        self.assertEqual(attack.card_type, RecommendationCardType.OBSERVATION)
        self.assertFalse(attack.is_action)
        self.assertEqual(attack.estimated_win_delta, 0.0)

    def test_defensive_warning_uses_correct_opponent_attack_mapping(self):
        result = match_result(
            formation(
                "3-5-2",
                0.42,
                recommended=True,
                team_ratings=ratings(left_defense=20, central_defense=50, right_defense=50),
                opponent_ratings=ratings(right_attack=32),
            )
        )

        recommendation = next(
            item for item in RecommendationEngine().recommend(result)
            if item.code == "weakness:right_attack->left_defense"
        )

        self.assertEqual(recommendation.card_type, RecommendationCardType.WARNING)
        self.assertEqual(recommendation.params["sector"], "{advisor.sector.left_defense}")

    def test_favorable_attack_concentration_is_observation(self):
        result = match_result(
            formation(
                "3-5-2",
                0.42,
                recommended=True,
                team_ratings=ratings(left_attack=45, central_attack=32, right_attack=31),
                opponent_ratings=ratings(left_defense=40, central_defense=38, right_defense=24),
            )
        )

        recommendation = next(
            item for item in RecommendationEngine().recommend(result)
            if item.code == "balance:attack_concentration"
        )

        self.assertEqual(recommendation.card_type, RecommendationCardType.OBSERVATION)
        self.assertEqual(
            recommendation.title_key,
            "advisor.rule.favorable_concentration.title",
        )

    def test_unfavorable_attack_concentration_is_warning(self):
        result = match_result(
            formation(
                "3-5-2",
                0.42,
                recommended=True,
                team_ratings=ratings(left_attack=45, central_attack=32, right_attack=31),
                opponent_ratings=ratings(left_defense=24, central_defense=38, right_defense=44),
            )
        )

        recommendation = next(
            item for item in RecommendationEngine().recommend(result)
            if item.code == "balance:attack_concentration"
        )

        self.assertEqual(recommendation.card_type, RecommendationCardType.WARNING)
        self.assertEqual(
            recommendation.title_key,
            "advisor.rule.unfavorable_concentration.title",
        )

    def test_low_possession_is_context_not_action(self):
        result = match_result(
            formation(
                "3-5-2",
                0.42,
                possession=0.40,
                recommended=True,
                team_ratings=ratings(left_attack=32, central_attack=32, right_attack=32),
                opponent_ratings=ratings(
                    left_defense=35,
                    central_defense=35,
                    right_defense=35,
                    left_attack=10,
                    central_attack=10,
                    right_attack=10,
                ),
            )
        )

        recommendation = next(
            item for item in RecommendationEngine().recommend(result)
            if item.code == "balance:possession"
        )

        self.assertEqual(recommendation.card_type, RecommendationCardType.OBSERVATION)
        self.assertEqual(recommendation.estimated_win_delta, 0.0)

    def test_beneficial_lineup_change_is_keep_action(self):
        result = match_result(
            formation("3-5-2", 0.414, recommended=True),
            change_analysis=lineup_change(0.014),
        )

        recommendation = next(
            item for item in RecommendationEngine().recommend(result)
            if item.code == "lineup:keep_last_change"
        )

        self.assertTrue(recommendation.is_action)
        self.assertEqual(recommendation.params["incoming"], "New Midfielder")

    def test_harmful_lineup_change_is_revert_action(self):
        result = match_result(
            formation("3-5-2", 0.386, recommended=True),
            change_analysis=lineup_change(-0.014),
        )

        recommendation = next(
            item for item in RecommendationEngine().recommend(result)
            if item.code == "lineup:revert_last_change"
        )

        self.assertTrue(recommendation.is_action)
        self.assertAlmostEqual(recommendation.estimated_win_delta, 0.014)

    def test_neutral_lineup_change_is_observation(self):
        result = match_result(
            formation("3-5-2", 0.400, recommended=True),
            change_analysis=lineup_change(0.0),
        )

        recommendation = next(
            item for item in RecommendationEngine().recommend(result)
            if item.code == "lineup:neutral_last_change"
        )

        self.assertEqual(recommendation.card_type, RecommendationCardType.OBSERVATION)

    def test_actions_rank_before_observations_and_are_capped(self):
        recommendations = [
            Recommendation(
                code=f"obs:{index}",
                title_key="advisor.title",
                explanation_key="advisor.empty",
                category=RecommendationCategory.STRENGTH,
                impact_score=10 + index,
                confidence=RecommendationConfidence.HIGH,
                card_type=RecommendationCardType.OBSERVATION,
            )
            for index in range(4)
        ] + [
            Recommendation(
                code=f"action:{index}",
                title_key="advisor.title",
                explanation_key="advisor.empty",
                category=RecommendationCategory.FORMATION,
                impact_score=0.001 + index,
                confidence=RecommendationConfidence.LOW,
                card_type=RecommendationCardType.ACTION,
                estimated_win_delta=0.001 + index,
            )
            for index in range(4)
        ]

        ranked = RecommendationRanker().rank(recommendations, limit=5)

        self.assertEqual([item.card_type for item in ranked[:3]], [
            RecommendationCardType.ACTION,
            RecommendationCardType.ACTION,
            RecommendationCardType.ACTION,
        ])
        self.assertEqual(len([item for item in ranked if item.is_action]), 3)

    def test_generic_strength_does_not_displace_actions(self):
        action = Recommendation(
            code="action:low",
            title_key="advisor.title",
            explanation_key="advisor.empty",
            category=RecommendationCategory.FORMATION,
            impact_score=0.001,
            confidence=RecommendationConfidence.LOW,
            card_type=RecommendationCardType.ACTION,
            estimated_win_delta=0.001,
        )
        strength = replace(
            action,
            code="strength:midfield",
            category=RecommendationCategory.STRENGTH,
            card_type=RecommendationCardType.OBSERVATION,
            impact_score=10.0,
            estimated_win_delta=0.0,
        )

        ranked = RecommendationRanker().rank([strength, action], limit=1)

        self.assertEqual(ranked[0].code, "action:low")

    def test_duplicate_recommendations_keep_highest_impact(self):
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

    def test_impact_badges_use_win_delta_not_confidence(self):
        high_confidence_low_impact = Recommendation(
            code="action:low",
            title_key="advisor.title",
            explanation_key="advisor.empty",
            category=RecommendationCategory.FORMATION,
            impact_score=0.001,
            confidence=RecommendationConfidence.HIGH,
            card_type=RecommendationCardType.ACTION,
            estimated_win_delta=0.001,
        )

        self.assertEqual(impact_band(high_confidence_low_impact), "low")
        self.assertEqual(high_confidence_low_impact.confidence, RecommendationConfidence.HIGH)

    def test_impact_thresholds_are_percentage_points(self):
        recommendation = Recommendation(
            code="action",
            title_key="advisor.title",
            explanation_key="advisor.empty",
            category=RecommendationCategory.FORMATION,
            impact_score=0.0,
            confidence=RecommendationConfidence.LOW,
            card_type=RecommendationCardType.ACTION,
        )

        self.assertEqual(impact_band(replace(recommendation, estimated_win_delta=0.015)), "high")
        self.assertEqual(impact_band(replace(recommendation, estimated_win_delta=0.005)), "medium")
        self.assertEqual(impact_band(replace(recommendation, estimated_win_delta=0.001)), "low")
        self.assertEqual(impact_band(replace(recommendation, estimated_win_delta=0.0)), "observation")

    def test_tiny_positive_delta_formats_below_point_one_pp(self):
        self.assertEqual(format_win_delta(0.0005), "Below 0.1 pp")

    def test_persistence_preserves_actionable_advisor_fields(self):
        result = with_tactical_advisor(
            match_result(
                formation("3-5-2", 0.40, recommended=True),
                formation("4-5-1", 0.42),
            )
        )

        restored = match_analysis_result_from_dict(
            match_analysis_result_to_dict(result)
        )
        original_action = next(item for item in result.tactical_advisor if item.is_action)
        restored_action = next(item for item in restored.tactical_advisor if item.is_action)

        self.assertEqual(restored_action.code, original_action.code)
        self.assertEqual(restored_action.card_type, RecommendationCardType.ACTION)
        self.assertEqual(restored_action.sector_deltas, original_action.sector_deltas)

    def test_english_and_spanish_advisor_strings_exist(self):
        for language in ("en", "es"):
            service = configure_localization(language)
            self.assertNotEqual(service.t("advisor.card.action"), "advisor.card.action")
            self.assertNotEqual(
                service.t(
                    "advisor.rule.use_formation.title",
                    formation="4-5-1",
                    current_formation="3-5-2",
                ),
                "advisor.rule.use_formation.title",
            )

    def test_advisor_does_not_import_optimizers(self):
        import engine.advisor.recommendation_engine as module

        self.assertNotIn("Optimizer", module.__dict__)


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class TacticalAdvisorViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        configure_localization("en")

    def test_match_page_renders_tactical_advisor(self):
        result = with_tactical_advisor(
            match_result(
                formation("3-5-2", 0.40, recommended=True),
                formation("4-5-1", 0.42),
            )
        )
        page = MatchPage()
        page.show_results(result)

        labels = [label.text() for label in page.findChildren(QLabel)]

        self.assertIn("Tactical Advisor", labels)
        self.assertIn("High Impact", labels)

    def test_observation_cards_do_not_render_estimated_win_badge(self):
        result = with_tactical_advisor(
            match_result(
                formation("3-5-2", 0.40, possession=0.40, recommended=True),
            )
        )
        page = MatchPage()
        page.show_results(result)

        labels = [label.text() for label in page.findChildren(QLabel)]

        self.assertIn("Observation", labels)
        self.assertFalse(any("Estimated +0.0 pp Win" == label for label in labels))

    def test_simple_verbosity_hides_explanations(self):
        result = with_tactical_advisor(
            match_result(
                formation("3-5-2", 0.40, recommended=True),
                formation("4-5-1", 0.42),
            )
        )
        page = MatchPage()
        page.set_advisor_verbosity("simple")
        page.show_results(result)

        labels = [label.text() for label in page.findChildren(QLabel)]

        self.assertNotIn(
            "This evaluated formation improves win probability by +2.0 pp. "
            "Sector changes: no major sector change.",
            labels,
        )
