import unittest
from dataclasses import replace

from engine.advisor.recommendation_engine import RecommendationEngine
from engine.match_intelligence import MatchIntelligenceEngine
from engine.match_intelligence.matchup import (
    opponent_defense_for_our_attack,
    own_defense_for_opponent_attack,
)
from engine.match_intelligence.matchup_analyzer import MatchupAnalyzer
from engine.match_intelligence.models import (
    MatchIntelligenceResult,
    MatchupInsight,
    MatchupMatrix,
    TeamProfile,
)
from ht_coach_app.core.localization import LocalizationService, configure_localization
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    SectorRatingComparisonResult,
    TeamRatingsResult,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
    with_tactical_advisor,
)

try:
    from PySide6.QtWidgets import QApplication, QLabel, QTableWidget
    from ht_coach_app.views.match_page import MatchPage
except Exception:
    QApplication = None
    QLabel = None
    QTableWidget = None
    MatchPage = None


def ratings(
    midfield=40,
    left_defense=35,
    central_defense=40,
    right_defense=45,
    left_attack=30,
    central_attack=42,
    right_attack=24,
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


def formation(team=None, opponent=None, possession=0.52):
    return FormationAnalysisResult(
        formation_name="3-5-2",
        recommended_tactic="NORMAL",
        tactic_level=5.0,
        win_probability=0.44,
        draw_probability=0.30,
        loss_probability=0.26,
        possession=possession,
        expected_goals=2.0,
        opponent_expected_goals=1.2,
        is_recommended=True,
        team_ratings=team or ratings(),
        opponent_ratings=opponent or ratings(
            midfield=38,
            left_defense=40,
            central_defense=34,
            right_defense=28,
            left_attack=55,
            central_attack=38,
            right_attack=30,
        ),
    )


def non_comparable_sector_comparisons():
    return [
        SectorRatingComparisonResult(
            matchup_key="midfield",
            our_sector="midfield",
            opponent_sector="midfield",
            our_value=40,
            opponent_value=7.25,
            our_scale="ht_coach_internal_contribution",
            opponent_scale="hattrick_decimal",
            difference=None,
            advantage="not_directly_comparable",
            comparable=False,
        )
    ]


def result(team=None, opponent=None, possession=0.52):
    return MatchAnalysisResult(
        player_count=20,
        opponent_name="Rival FC",
        analyzed_formations=["3-5-2"],
        formations=[formation(team, opponent, possession)],
    )


class MatchIntelligenceEngineTest(unittest.TestCase):
    def test_correct_matchup_mapping(self):
        self.assertEqual(
            opponent_defense_for_our_attack("left_attack"),
            "right_defense",
        )
        self.assertEqual(
            opponent_defense_for_our_attack("central_attack"),
            "central_defense",
        )
        self.assertEqual(
            opponent_defense_for_our_attack("right_attack"),
            "left_defense",
        )
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

    def test_classification_thresholds(self):
        analyzer = MatchupAnalyzer()

        self.assertEqual(analyzer.classify(8), "Excellent")
        self.assertEqual(analyzer.classify(4), "Favorable")
        self.assertEqual(analyzer.classify(0), "Balanced")
        self.assertEqual(analyzer.classify(-4), "Unfavorable")
        self.assertEqual(analyzer.classify(-8), "Critical")

    def test_opportunity_and_risk_detection(self):
        intelligence = MatchIntelligenceEngine().analyze(result())

        self.assertTrue(intelligence.opportunities)
        self.assertTrue(intelligence.risks)
        self.assertTrue(
            any(
                item.code.startswith("opportunity:our_attack:central_attack")
                for item in intelligence.opportunities
            )
        )
        self.assertTrue(
            any(
                item.code.startswith("risk:opponent_attack:left_attack")
                for item in intelligence.risks
            )
        )

    def test_focus_generation_returns_exactly_three_items(self):
        intelligence = MatchIntelligenceEngine().analyze(result())

        self.assertEqual(len(intelligence.tactical_focuses), 3)
        self.assertEqual(
            [item.code for item in intelligence.tactical_focuses],
            [
                "attack_best_route",
                "protect_exposed_defense",
                "midfield_battle",
            ],
        )

    def test_summary_generation_is_deterministic(self):
        intelligence = MatchIntelligenceEngine().analyze(result())

        self.assertEqual(
            intelligence.summary_key,
            "match_intelligence.summary.defensive_risk",
        )

    def test_matrix_marks_best_and_worst_routes(self):
        intelligence = MatchIntelligenceEngine().analyze(result())

        self.assertEqual(len(intelligence.matrix.our_attack_rows), 3)
        self.assertEqual(len(intelligence.matrix.opponent_attack_rows), 3)
        self.assertEqual(
            len(
                [
                    item for item in intelligence.matrix.our_attack_rows
                    if item.is_best_route
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                [
                    item for item in intelligence.matrix.our_attack_rows
                    if item.is_worst_route
                ]
            ),
            1,
        )

    def test_team_profiles_are_generated_for_both_teams(self):
        intelligence = MatchIntelligenceEngine().analyze(result())

        self.assertEqual(intelligence.our_profile.strongest_sector, "right_defense")
        self.assertEqual(intelligence.opponent_profile.strongest_sector, "left_attack")

    def test_persistence_round_trip_preserves_match_intelligence(self):
        enriched = MatchAnalysisResult(
            player_count=20,
            opponent_name="Rival FC",
            analyzed_formations=["3-5-2"],
            formations=[formation()],
            match_intelligence=MatchIntelligenceEngine().analyze(result()),
        )

        restored = match_analysis_result_from_dict(
            match_analysis_result_to_dict(enriched)
        )

        self.assertIsNotNone(restored.match_intelligence)
        self.assertEqual(
            restored.match_intelligence.matrix.our_attack_rows[0].code,
            enriched.match_intelligence.matrix.our_attack_rows[0].code,
        )

    def test_service_enrichment_adds_match_intelligence(self):
        enriched = with_tactical_advisor(
            MatchAnalysisResult(
                player_count=20,
                opponent_name="Rival FC",
                analyzed_formations=["3-5-2"],
                formations=[formation()],
                match_intelligence=MatchIntelligenceEngine().analyze(result()),
            )
        )

        self.assertIsNotNone(enriched.match_intelligence)

    def test_advisor_consumes_match_intelligence_matchups(self):
        intelligence = MatchIntelligenceResult(
            formation_name="3-5-2",
            our_profile=TeamProfile("midfield", "right_attack", "attack", "left_defense"),
            opponent_profile=TeamProfile("central_defense", "right_defense", "defense", "right_defense"),
            our_attack_matchups=(
                MatchupInsight(
                    code="our_attack:left_attack->right_defense",
                    perspective="our_attack",
                    attack_sector="left_attack",
                    defense_sector="right_defense",
                    attack_value=20,
                    defense_value=40,
                    difference=-20,
                    classification="Critical",
                    advantage="opponent",
                    interpretation_key="match_intelligence.interpretation.our_attack.critical",
                ),
            ),
            opponent_attack_matchups=(),
            matrix=MatchupMatrix(),
        )
        match_result = MatchAnalysisResult(
            player_count=20,
            opponent_name="Rival FC",
            analyzed_formations=["3-5-2"],
            formations=[
                formation(
                    team=ratings(left_attack=50),
                    opponent=ratings(right_defense=10),
                )
            ],
            match_intelligence=intelligence,
        )

        recommendations = RecommendationEngine().recommend(match_result)

        self.assertIn(
            "attack_matchup:left_attack->right_defense",
            [item.code for item in recommendations],
        )

    def test_workspace_refresh_reflects_current_evaluated_result(self):
        first = MatchIntelligenceEngine().analyze(
            result(
                team=ratings(left_attack=50, central_attack=30, right_attack=24),
                opponent=ratings(left_defense=40, central_defense=34, right_defense=28),
            )
        )
        refreshed = MatchIntelligenceEngine().analyze(
            result(
                team=ratings(left_attack=20, central_attack=52, right_attack=24),
                opponent=ratings(left_defense=40, central_defense=34, right_defense=28),
            )
        )

        self.assertNotEqual(
            [
                item.attack_sector
                for item in first.matrix.our_attack_rows
                if item.is_best_route
            ],
            [
                item.attack_sector
                for item in refreshed.matrix.our_attack_rows
                if item.is_best_route
            ],
        )

    def test_localization_resolves_match_intelligence_keys(self):
        for language in ("en", "es"):
            service = LocalizationService(language)
            text = service.t(
                "match_intelligence.focus.attack_best_route.title",
                attack_sector=service.t("match_intelligence.sector.central_attack"),
            )
            self.assertFalse(text.startswith("match_intelligence."))


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class MatchIntelligenceViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        configure_localization("en")

    def test_match_page_renders_match_intelligence_panel(self):
        match_result = MatchAnalysisResult(
            player_count=20,
            opponent_name="Rival FC",
            analyzed_formations=["3-5-2"],
            formations=[formation()],
            match_intelligence=MatchIntelligenceEngine().analyze(result()),
        )
        page = MatchPage()
        page.show_results(match_result)

        labels = [label.text() for label in page.findChildren(QLabel)]

        self.assertIn("Match Intelligence", labels)
        self.assertIn("Tactical Focus", labels)

    def test_rendering_data_is_deterministic(self):
        match_result = MatchAnalysisResult(
            player_count=20,
            opponent_name="Rival FC",
            analyzed_formations=["3-5-2"],
            formations=[formation()],
            match_intelligence=MatchIntelligenceEngine().analyze(result()),
        )
        page = MatchPage()

        rows = page.match_intelligence_rows(match_result)

        self.assertEqual(rows["formation"], "3-5-2")
        self.assertEqual(rows["focuses"][0], "attack_best_route")
        self.assertEqual(len(rows["our_attack_matrix"]), 3)

    def test_incompatible_scales_hide_matchup_differences_and_classes(self):
        match_result = MatchAnalysisResult(
            player_count=20,
            opponent_name="Rival FC",
            analyzed_formations=["3-5-2"],
            formations=[
                replace(
                    formation(),
                    sector_rating_comparisons=(
                        non_comparable_sector_comparisons()
                    ),
                )
            ],
            match_intelligence=MatchIntelligenceEngine().analyze(result()),
        )
        page = MatchPage()
        page.show_results(match_result)

        labels = [label.text() for label in page.findChildren(QLabel)]
        rows = page.match_intelligence_rows(match_result)

        self.assertTrue(
            any("Direct margins and advantage classes are hidden" in text for text in labels)
        )
        self.assertEqual(
            page._visible_match_intelligence_focuses(
                match_result.match_intelligence,
                comparable=False,
            )[0].code,
            "midfield_battle",
        )
        self.assertTrue(rows["ratings_comparable"] is False)
        self.assertNotIn("+", " ".join(labels))
        self.assertNotIn("Excellent", labels)

    def test_rating_calibration_hides_difference_column_when_not_comparable(self):
        match_result = MatchAnalysisResult(
            player_count=20,
            opponent_name="Rival FC",
            analyzed_formations=["3-5-2"],
            formations=[
                replace(
                    formation(),
                    sector_rating_comparisons=(
                        non_comparable_sector_comparisons()
                    ),
                )
            ],
        )
        page = MatchPage()
        page.show_results(match_result)

        headers = []
        for table in page.findChildren(QTableWidget):
            headers.append(
                [
                    table.horizontalHeaderItem(column).text()
                    for column in range(table.columnCount())
                ]
            )

        self.assertIn(
            ["Matchup", "HT Coach rating", "Opponent rating", "Assessment"],
            headers,
        )
