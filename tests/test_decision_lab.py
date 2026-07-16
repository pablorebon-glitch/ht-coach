import unittest

from ht_coach_app.reasoning.decision_lab import DecisionLab
from ht_coach_app.reasoning.explanation_formatter import (
    format_decision_lab_copy,
)
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
        left_defense=24,
        central_defense=30,
        right_defense=25,
        midfield=32,
        left_attack=31,
        central_attack=28,
        right_attack=22,
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
    def test_meaningful_win_advantage_and_xg_reason(self):
        analysis = DecisionLab().analyze(
            result(
                formation("3-5-2", 0.58, xg=2.4),
                formation("4-5-1", 0.52, xg=1.8),
            )
        )

        self.assertEqual(analysis.confidence.level, "HIGH")
        self.assertIn(
            "Win probability edge",
            [reason.title for reason in analysis.reasons]
        )
        self.assertIn(
            "Expected goals trade-off",
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
            "Possession profile",
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
            "Opponent xG",
            [risk.title for risk in analysis.risks]
        )
        self.assertTrue(analysis.our_vulnerabilities)

    def test_strongest_attacking_channel(self):
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
        self.assertIn(
            "Best attacking channel",
            [reason.title for reason in analysis.reasons]
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

    def test_single_formation_confidence_is_medium(self):
        analysis = DecisionLab().analyze(
            result(formation("3-5-2", 0.56))
        )

        self.assertEqual(analysis.confidence.level, "MEDIUM")

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
        self.assertIn("HT Coach Decision Lab", copy_text)
        self.assertNotIn("GOALKEEPER", copy_text)

    def test_output_is_deterministic(self):
        match = result(
            formation("3-5-2", 0.58, xg=2.4),
            formation("4-5-1", 0.52, xg=1.8),
        )

        first = DecisionLab().analyze(match)
        second = DecisionLab().analyze(match)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
