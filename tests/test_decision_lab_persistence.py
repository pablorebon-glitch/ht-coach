import unittest
from dataclasses import asdict

from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    TeamRatingsResult,
    format_decision_lab,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
)


class DecisionLabPersistenceTest(unittest.TestCase):
    def test_serialization_round_trip(self):
        result = MatchAnalysisResult(
            player_count=1,
            opponent_name="Rival FC",
            analyzed_formations=["3-5-2"],
            formations=[
                FormationAnalysisResult(
                    formation_name="3-5-2",
                    recommended_tactic="Normal",
                    tactic_level=0,
                    win_probability=0.55,
                    draw_probability=0.25,
                    loss_probability=0.20,
                    possession=0.56,
                    expected_goals=2.0,
                    opponent_expected_goals=1.0,
                    is_recommended=True,
                    team_ratings=TeamRatingsResult(
                        left_attack=34,
                        central_attack=30,
                        right_attack=25,
                        left_defense=30,
                        central_defense=32,
                        right_defense=29,
                    ),
                    opponent_ratings=TeamRatingsResult(
                        left_defense=24,
                        central_defense=28,
                        right_defense=25,
                        left_attack=25,
                        central_attack=26,
                        right_attack=24,
                    ),
                    baseline_win_probability=0.45,
                    best_normal_win_probability=0.50,
                    best_order_win_probability=0.53,
                    final_optimized_win_probability=0.55,
                    lineup_gain=0.05,
                    order_gain=0.03,
                    tactic_gain=0.02,
                    total_gain=0.10,
                )
            ]
        )
        restored = match_analysis_result_from_dict(
            match_analysis_result_to_dict(result)
        )

        self.assertIsNotNone(restored.decision_lab)
        self.assertEqual(
            restored.decision_lab.recommended_formation.formation,
            "3-5-2"
        )

    def test_backward_compatibility_regenerates_missing_reasoning(self):
        restored = match_analysis_result_from_dict(
            {
                "player_count": 1,
                "opponent_name": "Rival FC",
                "formations": [
                    {
                        "formation_name": "3-5-2",
                        "recommended_tactic": "Normal",
                        "tactic_level": 0,
                        "win_probability": 0.55,
                        "draw_probability": 0.25,
                        "loss_probability": 0.20,
                        "possession": 0.56,
                        "expected_goals": 2.0,
                        "opponent_expected_goals": 1.0,
                        "is_recommended": True,
                    }
                ],
            }
        )

        self.assertIsNotNone(restored.decision_lab)

    def test_malformed_reasoning_does_not_crash(self):
        restored = match_analysis_result_from_dict(
            {
                "player_count": 0,
                "opponent_name": "",
                "decision_lab": {"confidence": "bad"},
                "formations": [],
            }
        )

        self.assertIsNone(restored.decision_lab)
        self.assertEqual(
            format_decision_lab(restored),
            "No Decision Lab result available."
        )


if __name__ == "__main__":
    unittest.main()
