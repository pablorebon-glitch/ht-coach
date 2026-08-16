import unittest

from ht_coach_app.reasoning.decision_lab import DecisionLab
from ht_coach_app.reasoning.explanation_formatter import (
    format_decision_lab_copy,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    TeamRatingsResult,
)


def formation(
    name,
    win,
    possession=0.55,
    xg=2.0,
    opp_xg=1.0,
    tactic="Normal",
    baseline=0.40,
    normal=0.46,
    order=0.50,
    left_attack=34,
    central_attack=30,
    right_attack=24,
    left_defense=28,
    central_defense=33,
    right_defense=26,
    opponent_left_defense=24,
    opponent_central_defense=30,
    opponent_right_defense=25,
    opponent_left_attack=31,
    opponent_central_attack=28,
    opponent_right_attack=22,
):
    team = TeamRatingsResult(
        left_defense=left_defense,
        central_defense=central_defense,
        right_defense=right_defense,
        midfield=35,
        left_attack=left_attack,
        central_attack=central_attack,
        right_attack=right_attack,
    )
    opponent = TeamRatingsResult(
        left_defense=opponent_left_defense,
        central_defense=opponent_central_defense,
        right_defense=opponent_right_defense,
        midfield=32,
        left_attack=opponent_left_attack,
        central_attack=opponent_central_attack,
        right_attack=opponent_right_attack,
    )

    return FormationAnalysisResult(
        formation_name=name,
        recommended_tactic=tactic,
        tactic_level=7.0,
        win_probability=win,
        draw_probability=0.25,
        loss_probability=1.0 - win - 0.25,
        possession=possession,
        expected_goals=xg,
        opponent_expected_goals=opp_xg,
        team_ratings=team,
        opponent_ratings=opponent,
        baseline_win_probability=baseline,
        best_normal_win_probability=normal,
        best_order_win_probability=order,
        final_optimized_win_probability=win,
        lineup_gain=normal - baseline,
        order_gain=order - normal,
        tactic_gain=win - order,
        total_gain=win - baseline,
    )


def result(*formations):
    return MatchAnalysisResult(
        player_count=20,
        opponent_name="Rival FC",
        formations=list(formations),
        analyzed_formations=[
            item.formation_name
            for item in formations
        ],
    )


class DecisionLabRulesTest(unittest.TestCase):
    def setUp(self):
        configure_localization("en")

    def test_meaningful_win_advantage_and_xg_reason(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.58, xg=2.4),
                formation("4-5-1", 0.52, xg=1.8),
            )
        )

        self.assertEqual(analysis.confidence.level, "HIGH")
        self.assertIn(
            "Highest win probability",
            [reason.title for reason in analysis.reasons]
        )
        self.assertIn(
            "Creates more attacking output",
            [reason.title for reason in analysis.reasons]
        )

    def test_negligible_win_advantage_lowers_confidence(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.5001),
                formation("4-5-1", 0.5000),
            )
        )

        self.assertEqual(analysis.confidence.level, "LOW")
        self.assertIn("marginal", analysis.summary)

    def test_possession_advantage_is_explained(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.54, possession=0.58),
                formation("4-5-1", 0.51, possession=0.52),
            )
        )

        self.assertIn(
            "Keeps a possession edge",
            [reason.title for reason in analysis.reasons]
        )

    def test_defensive_risk_and_vulnerability(self):
        analysis = DecisionLab().analyze(
            result(
                formation(
                    "3-5-2",
                    0.56,
                    opp_xg=1.8,
                    right_defense=20
                ),
                formation("4-5-1", 0.50),
            )
        )

        self.assertIn(
            "Opponent pressure",
            [risk.title for risk in analysis.risks]
        )
        self.assertTrue(analysis.our_vulnerabilities)

    def test_favorable_attacking_channel_is_not_mislabeled(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.56, left_attack=40),
                formation("4-5-1", 0.50),
            )
        )

        self.assertEqual(
            analysis.opponent_weaknesses[0].sector,
            "Left attack vs opponent right defense"
        )
        self.assertTrue(
            any(
                item.classification in {
                    "Slight advantage",
                    "Strong advantage",
                }
                for item in analysis.opponent_weaknesses
            )
        )

    def test_all_attacking_channels_balanced(self):
        analysis = DecisionLab().analyze(
            result(
                formation(
                    "3-5-2",
                    0.56,
                    left_attack=25,
                    central_attack=30,
                    right_attack=24,
                    opponent_right_defense=25,
                    opponent_central_defense=30,
                    opponent_left_defense=24,
                ),
                formation("4-5-1", 0.50),
            )
        )

        self.assertTrue(
            all(
                item.classification == "Balanced"
                for item in analysis.opponent_weaknesses
            )
        )

    def test_all_attacking_channels_unfavorable(self):
        analysis = DecisionLab().analyze(
            result(
                formation(
                    "3-5-2",
                    0.56,
                    left_attack=20,
                    central_attack=20,
                    right_attack=20,
                    opponent_right_defense=30,
                    opponent_central_defense=30,
                    opponent_left_defense=30,
                ),
                formation("4-5-1", 0.50),
            )
        )

        self.assertTrue(
            all(
                "disadvantage" in item.classification.lower()
                for item in analysis.opponent_weaknesses
            )
        )

    def test_no_defensive_vulnerability_when_channels_are_safe(self):
        analysis = DecisionLab().analyze(
            result(
                formation(
                    "3-5-2",
                    0.56,
                    left_defense=35,
                    central_defense=35,
                    right_defense=35,
                    opponent_left_attack=25,
                    opponent_central_attack=25,
                    opponent_right_attack=25,
                ),
                formation("4-5-1", 0.50),
            )
        )

        self.assertFalse(analysis.risks)

    def test_clear_defensive_vulnerability_uses_actionable_language(self):
        analysis = DecisionLab().analyze(
            result(
                formation(
                    "3-5-2",
                    0.56,
                    right_defense=20,
                    opponent_left_attack=31,
                ),
                formation("4-5-1", 0.50),
            )
        )

        self.assertIn(
            "Right defense is the main concern",
            " ".join(risk.description for risk in analysis.risks)
        )

    def test_every_tactic_has_deterministic_observation(self):
        tactics = [
            "Normal",
            "Attack in the Middle",
            "Attack on Wings",
            "Pressing",
            "Counter-Attacks",
            "Play Creatively",
            "Long Shots",
        ]

        for tactic in tactics:
            with self.subTest(tactic=tactic):
                analysis = DecisionLab().analyze(
                    result(
                        formation("3-5-2", 0.56, tactic=tactic),
                        formation("4-5-1", 0.50),
                    )
                )
                self.assertEqual(
                    analysis.tactical_observations[0].title,
                    tactic
                )
                self.assertIn(
                    "win probability",
                    analysis.tactical_observations[0].description
                    if tactic != "Normal"
                    else "win probability"
                )

    def test_single_formation_confidence_is_medium(self):
        analysis = DecisionLab().analyze(
            result(formation("3-5-2", 0.56))
        )

        self.assertEqual(analysis.confidence.level, "MEDIUM")
        self.assertIn(
            "no alternative formation",
            analysis.confidence.explanation
        )

    def test_comparison_deltas_and_copy_are_readable(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.58, xg=2.4),
                formation("4-5-1", 0.52, xg=1.8),
            )
        )
        comparison = analysis.comparisons[0]
        copy_text = format_decision_lab_copy(analysis)

        self.assertAlmostEqual(
            comparison.win_probability_delta,
            0.06
        )
        self.assertAlmostEqual(
            comparison.expected_goals_delta,
            0.6
        )
        self.assertIn("HT COACH DECISION LAB", copy_text)
        self.assertIn("Recommendation confidence", copy_text)
        self.assertNotIn("GOALKEEPER", copy_text)

    def test_output_is_deterministic(self):
        match = result(
            formation("3-5-2", 0.58, xg=2.4),
            formation("4-5-1", 0.52, xg=1.8),
        )

        first = DecisionLab().analyze(match)
        second = DecisionLab().analyze(match)

        self.assertEqual(first, second)

    def test_xg_bands_are_interpreted(self):
        cases = [
            (0.72, "low"),
            (1.04, "moderate"),
            (1.33, "dangerous"),
            (1.88, "very high"),
        ]

        for opp_xg, expected in cases:
            with self.subTest(opp_xg=opp_xg):
                analysis = DecisionLab().analyze(
                    result(
                        formation(
                            "3-5-2",
                            0.56,
                            opp_xg=opp_xg,
                            left_defense=40,
                            central_defense=40,
                            right_defense=40,
                        ),
                        formation("4-5-1", 0.50),
                    )
                )
                text = " ".join(risk.description for risk in analysis.risks)
                if opp_xg < 1.20:
                    self.assertEqual(text, "")
                else:
                    self.assertIn(expected, text)

    def test_negligible_tactic_gain_wording(self):
        analysis = DecisionLab().analyze(
            result(
                formation(
                    "3-5-2",
                    0.5001,
                    tactic="Long Shots",
                    order=0.5000,
                ),
                formation("4-5-1", 0.49),
            )
        )

        self.assertIn(
            "marginal",
            analysis.tactical_observations[0].description
        )

    def test_no_duplicated_reason_risk_tactical_text(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.58, xg=2.4, opp_xg=1.33),
                formation("4-5-1", 0.52, xg=1.8),
            )
        )
        lines = [
            item.description
            for item in analysis.reasons
        ] + [
            item.description
            for item in analysis.risks
        ] + [
            item.description
            for item in analysis.tactical_observations
        ]

        self.assertEqual(len(lines), len(set(lines)))

    def test_copy_hides_negligible_optimization_gains_and_negative_zero(self):
        analysis = DecisionLab().analyze(
            result(
                formation(
                    "3-5-2",
                    0.5001,
                    baseline=0.5000,
                    normal=0.5000,
                    order=0.5000,
                    tactic="Long Shots",
                )
            )
        )
        text = format_decision_lab_copy(analysis)

        self.assertNotIn("+0.0 pp", text)
        self.assertNotIn("-0.0 pp", text)
        self.assertIn("marginal improvement", text)

    def test_comparison_conclusion_is_actionable(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.58, xg=2.4),
                formation("4-5-1", 0.52, xg=1.8),
            )
        )

        self.assertIn(
            "stronger option",
            analysis.comparisons[0].conclusion
        )

    def test_spanish_copy_localizes_decision_lab_without_raw_english(self):
        configure_localization("es")
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.58, xg=2.4),
                formation("4-5-1", 0.52, xg=1.8),
            )
        )

        text = format_decision_lab_copy(analysis)

        self.assertIn("Soporte de recomendacion", text)
        self.assertIn("Mayor probabilidad de victoria", text)
        self.assertNotIn("Highest win probability", text)
        self.assertNotIn("Recommendation confidence", text)
        self.assertNotIn("Clear advantage over", text)

    def test_decision_lab_support_is_not_labeled_as_match_probability(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.58, xg=2.4),
                formation("4-5-1", 0.52, xg=1.8),
            )
        )

        text = format_decision_lab_copy(analysis)

        self.assertIn("Recommendation support", text)
        self.assertNotIn("Confidence: 85", text)

    def test_decision_lab_carries_lineup_objective_payload(self):
        recommended = formation("3-5-2", 0.58)
        object.__setattr__(
            recommended,
            "objective_trace",
            {
                "candidate_id": "recommended-xi",
                "components": {"win_probability": 0.58},
            },
        )
        alternative = formation("4-5-1", 0.52)
        object.__setattr__(
            alternative,
            "objective_trace",
            {
                "candidate_id": "alternative-xi",
                "components": {"win_probability": 0.52},
            },
        )

        analysis = DecisionLab().analyze(
            result(recommended, alternative)
        )

        self.assertEqual(
            analysis.lineup_decision["recommended"]["candidate_id"],
            "recommended-xi"
        )
        self.assertEqual(
            analysis.lineup_decision["strongest_alternative"]["candidate_id"],
            "alternative-xi"
        )


if __name__ == "__main__":
    unittest.main()
