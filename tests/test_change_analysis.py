import unittest
from dataclasses import replace

from ht_coach_app.change_analysis.service import ChangeAnalysisService
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    TeamRatingsResult,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
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


def result(
    win,
    draw,
    loss,
    midfield,
    central_attack,
    right_defense=26,
):
    return MatchAnalysisResult(
        player_count=20,
        opponent_name="Rival FC",
        analyzed_formations=["3-5-2"],
        formations=[
            FormationAnalysisResult(
                formation_name="3-5-2",
                recommended_tactic="NORMAL",
                tactic_level=5.0,
                win_probability=win,
                draw_probability=draw,
                loss_probability=loss,
                possession=0.55,
                expected_goals=2.0,
                opponent_expected_goals=1.0,
                is_recommended=True,
                team_ratings=TeamRatingsResult(
                    midfield=midfield,
                    central_attack=central_attack,
                    right_defense=right_defense,
                ),
            )
        ],
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
                score_difference=1.25,
                previous_slot_score=7.5,
                current_slot_score=8.75,
            ),
        )
    )


class ChangeAnalysisServiceTest(unittest.TestCase):
    def test_last_change_and_position_fit_are_detected(self):
        analysis = ChangeAnalysisService().analyze(
            result(0.40, 0.30, 0.30, 39, 28),
            result(0.43, 0.30, 0.27, 42, 31),
            workspace_state(),
        )

        self.assertEqual(analysis.last_change.incoming_player, "New Midfielder")
        self.assertEqual(analysis.last_change.outgoing_player, "Old Midfielder")
        self.assertEqual(analysis.position_fit.difference, 1.25)

    def test_team_impact_comparison_uses_calculated_values(self):
        analysis = ChangeAnalysisService().analyze(
            result(0.40, 0.30, 0.30, 39, 28),
            result(0.43, 0.29, 0.28, 42, 31),
            workspace_state(),
        )

        self.assertEqual(
            [(item.label, round(item.difference, 2)) for item in analysis.team_impact],
            [("Win", 0.03), ("Draw", -0.01), ("Loss", -0.02)],
        )

    def test_sector_filtering_hides_unchanged_values(self):
        analysis = ChangeAnalysisService().analyze(
            result(0.40, 0.30, 0.30, 39, 28, right_defense=26),
            result(0.43, 0.29, 0.28, 42, 31, right_defense=26),
            workspace_state(),
        )

        self.assertEqual(
            [item.label for item in analysis.sector_changes],
            ["Midfield", "Central Attack"],
        )

    def test_summary_generation_is_deterministic(self):
        analysis = ChangeAnalysisService().analyze(
            result(0.40, 0.30, 0.30, 39, 28),
            result(0.43, 0.29, 0.27, 42, 31),
            workspace_state(),
        )

        self.assertEqual(analysis.summary.code, "excellent_tradeoff")

    def test_net_negative_summary_when_probabilities_worsen(self):
        analysis = ChangeAnalysisService().analyze(
            result(0.40, 0.30, 0.30, 39, 28),
            result(0.38, 0.30, 0.32, 42, 31),
            workspace_state(),
        )

        self.assertEqual(analysis.summary.code, "net_negative")

    def test_result_persistence_preserves_change_analysis(self):
        analysis = ChangeAnalysisService().analyze(
            result(0.40, 0.30, 0.30, 39, 28),
            result(0.43, 0.29, 0.28, 42, 31),
            workspace_state(),
        )
        stored = replace(
            result(0.43, 0.29, 0.28, 42, 31),
            change_analysis=analysis,
        )

        restored = match_analysis_result_from_dict(
            match_analysis_result_to_dict(stored)
        )

        self.assertEqual(
            restored.change_analysis.last_change.incoming_player,
            "New Midfielder",
        )


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class ChangeAnalysisViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_match_page_renders_change_analysis_panel(self):
        analysis = ChangeAnalysisService().analyze(
            result(0.40, 0.30, 0.30, 39, 28),
            result(0.43, 0.29, 0.28, 42, 31),
            workspace_state(),
        )
        page = MatchPage()
        page.show_results(
            replace(
                result(0.43, 0.29, 0.28, 42, 31),
                change_analysis=analysis,
            )
        )

        labels = [
            label.text()
            for label in page.findChildren(QLabel)
        ]

        self.assertIn("Change Analysis", labels)
        self.assertIn("Last Change", labels)
        self.assertIn("Position Fit", labels)
