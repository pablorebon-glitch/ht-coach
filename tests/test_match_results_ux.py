import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceRepository,
    MatchWorkspaceSettings,
)
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    format_decision_lab,
    format_match_summary,
    format_recommended_lineup,
)
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.opponent import Opponent
from models.order import Order
from models.position import Position
from models.side import Side
from models.tactic import Tactic
from models.team_ratings import TeamRatings


class FakeOpponentService:
    def __init__(self):
        self.opponent = Opponent(
            name="Rival FC",
            ratings=TeamRatings(
                left_defense=25,
                central_defense=35,
                right_defense=24,
                midfield=40,
                left_attack=25,
                central_attack=30,
                right_attack=24,
            )
        )

    def list_opponents(self):
        return [self.opponent]

    def get_opponent(self, name):
        if name == self.opponent.name:
            return self.opponent

        return None


def fake_importer(_path):
    return [
        SimpleNamespace(name="Keeper"),
        SimpleNamespace(name="Defender"),
    ]


def fake_optimizer(players, formations, _opponent_ratings):
    lineup = Lineup(
        players=[
            LineupPlayer(
                player=players[0],
                position=Position.GOALKEEPER,
                side=Side.CENTER,
                order=Order.NORMAL,
            ),
            LineupPlayer(
                player=players[1],
                position=Position.CENTRAL_DEFENDER,
                side=Side.LEFT,
                order=Order.DEFENSIVE,
                order_side=Side.LEFT,
            ),
        ]
    )

    results = []

    for index, formation in enumerate(formations):
        results.append(
            SimpleNamespace(
                formation=formation,
                lineup=lineup,
                tactic=Tactic.PRESSING,
                tactic_level=7.25 - index,
                probabilities=SimpleNamespace(
                    win=0.55 - index * 0.10,
                    draw=0.25,
                    loss=0.20 + index * 0.10,
                ),
                match_evaluation=SimpleNamespace(
                    possession=0.61 - index * 0.03,
                    expected_goals=2.1 - index * 0.4,
                    opponent_expected_goals=1.2 + index * 0.2,
                ),
            )
        )

    return results


class MatchResultsUxTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "players.csv"
        self.csv_path.write_text(
            "placeholder",
            encoding="utf-8"
        )
        self.service = MatchWorkspaceService(
            FakeOpponentService(),
            importer=fake_importer,
            optimizer=fake_optimizer
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_comparison_mapping_marks_recommended_and_deltas(self):
        result = self.service.analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2", "4-5-1"]
        )

        self.assertEqual(
            result.recommended_formation.formation_name,
            "3-5-2"
        )
        self.assertTrue(
            result.formations[0].is_recommended
        )
        self.assertFalse(
            result.formations[1].is_recommended
        )
        self.assertEqual(
            result.formations[0].win_probability_delta,
            0.0
        )
        self.assertAlmostEqual(
            result.formations[1].win_probability_delta,
            -0.10
        )
        self.assertEqual(
            result.formations[0].lineup[0].number,
            1
        )

    def test_result_persistence_round_trip(self):
        result = self.service.analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2", "4-5-1"]
        )
        repository = MatchWorkspaceRepository(
            Path(self.temp_dir.name) / "settings.json",
            Path(self.temp_dir.name) / "last_result.json"
        )

        repository.save_last_result(result)
        restored = repository.load_last_result()

        self.assertEqual(
            restored.opponent_name,
            "Rival FC"
        )
        self.assertEqual(
            restored.players_csv_filename,
            "players.csv"
        )
        self.assertEqual(
            restored.recommended_formation.formation_name,
            "3-5-2"
        )

    def test_clipboard_summary_formatting_is_readable(self):
        result = self.service.analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2"]
        )

        summary = format_match_summary(result)
        lineup = format_recommended_lineup(result)
        decision_lab = format_decision_lab(result)

        self.assertIn(
            "Recommended formation: 3-5-2",
            summary
        )
        self.assertIn(
            "Decision Lab",
            summary
        )
        self.assertIn(
            "HT COACH DECISION LAB",
            decision_lab
        )
        self.assertIn(
            "Recommendation confidence",
            decision_lab
        )
        self.assertIn(
            "Win: 55.0%",
            summary
        )
        self.assertIn(
            "No. | Side | Position | Player | Order | Order side",
            lineup
        )
        self.assertIn(
            "1 | CENTER | Goalkeeper (GK) | Keeper | Normal | -",
            lineup
        )

    def test_result_mapping_handles_more_than_two_formations(self):
        result = self.service.analyze(
            self.csv_path,
            "Rival FC",
            ["2-5-3", "3-5-2", "4-5-1"]
        )

        self.assertEqual(
            [
                formation.formation_name
                for formation in result.formations
            ],
            ["2-5-3", "3-5-2", "4-5-1"]
        )
        self.assertEqual(
            [
                formation.is_recommended
                for formation in result.formations
            ],
            [True, False, False]
        )
        self.assertIsNotNone(
            result.decision_lab
        )

    def test_deterministic_rendering_data(self):
        result = self.service.analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2", "4-5-1"]
        )

        rows = [
            (
                formation.formation_name,
                formation.is_recommended,
                round(formation.win_probability_delta, 2),
                round(formation.expected_goals_delta, 2),
            )
            for formation in result.formations
        ]

        self.assertEqual(
            rows,
            [
                ("3-5-2", True, 0.0, 0.0),
                ("4-5-1", False, -0.1, -0.4),
            ]
        )


try:
    from PySide6.QtWidgets import QApplication
    from ht_coach_app.views.match_page import MatchPage
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QApplication = None
    MatchPage = None


@unittest.skipIf(
    QApplication is None,
    "PySide6 is not installed"
)
class MatchResultsViewStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_empty_loading_error_success_states(self):
        page = MatchPage()

        self.assertEqual(
            page.current_state(),
            "empty"
        )

        page.show_loading()

        self.assertEqual(
            page.current_state(),
            "loading"
        )

        page.show_error("Bad CSV")

        self.assertEqual(
            page.current_state(),
            "error"
        )

        page.show_results(
            MatchAnalysisResult(
                player_count=2,
                opponent_name="Rival FC",
                players_csv_filename="players.csv",
                analyzed_formations=["3-5-2"],
                completed_at="2026-07-15 10:00:00",
                formations=[
                    FormationAnalysisResult(
                        formation_name="3-5-2",
                        recommended_tactic="Pressing",
                        tactic_level=7.25,
                        win_probability=0.55,
                        draw_probability=0.25,
                        loss_probability=0.20,
                        possession=0.61,
                        expected_goals=2.1,
                        opponent_expected_goals=1.2,
                        is_recommended=True,
                        lineup=[
                            LineupPlayerResult(
                                number=1,
                                position="Goalkeeper (GK)",
                                side="CENTER",
                                order="Normal",
                                order_side="",
                                player_name="Keeper"
                            )
                        ]
                    )
                ]
            )
        )

        self.assertEqual(
            page.current_state(),
            "success"
        )
        self.assertEqual(
            page.recommended_rows(
                MatchAnalysisResult(
                    player_count=0,
                    opponent_name="",
                    formations=[
                        FormationAnalysisResult(
                            formation_name="3-5-2",
                            recommended_tactic="Normal",
                            tactic_level=0,
                            win_probability=0,
                            draw_probability=0,
                            loss_probability=0,
                            possession=0,
                            expected_goals=0,
                            opponent_expected_goals=0,
                            is_recommended=True,
                        )
                    ]
                )
            ),
            ["3-5-2"]
        )

    def test_decision_lab_rendering_data_is_deterministic(self):
        page = MatchPage()
        result = MatchAnalysisResult(
            player_count=0,
            opponent_name="",
            formations=[
                FormationAnalysisResult(
                    formation_name="3-5-2",
                    recommended_tactic="Normal",
                    tactic_level=0,
                    win_probability=0.56,
                    draw_probability=0.24,
                    loss_probability=0.20,
                    possession=0.55,
                    expected_goals=1.5,
                    opponent_expected_goals=1.0,
                    is_recommended=True,
                )
            ],
        )
        from ht_coach_app.reasoning.decision_lab import DecisionLab

        result = MatchAnalysisResult(
            player_count=result.player_count,
            opponent_name=result.opponent_name,
            formations=result.formations,
            decision_lab=DecisionLab().analyze(result),
        )

        rows = page.decision_lab_rows(result)

        self.assertEqual(rows["formation"], "3-5-2")
        self.assertEqual(rows["confidence"], "MEDIUM")

    def test_decision_lab_summary_prefers_stable_recommendation_identity(self):
        from ht_coach_app.reasoning.decision_lab import DecisionLab

        page = MatchPage()
        stale_source = MatchAnalysisResult(
            player_count=0,
            opponent_name="",
            formations=[
                FormationAnalysisResult(
                    formation_name="3-5-2",
                    recommended_tactic="Normal",
                    tactic_level=0,
                    win_probability=0.61,
                    draw_probability=0.20,
                    loss_probability=0.19,
                    possession=0.55,
                    expected_goals=1.8,
                    opponent_expected_goals=0.9,
                    is_recommended=True,
                ),
                FormationAnalysisResult(
                    formation_name="2-5-3",
                    recommended_tactic="Normal",
                    tactic_level=0,
                    win_probability=0.50,
                    draw_probability=0.25,
                    loss_probability=0.25,
                    possession=0.52,
                    expected_goals=1.4,
                    opponent_expected_goals=1.1,
                ),
            ],
        )
        result = MatchAnalysisResult(
            player_count=0,
            opponent_name="",
            formations=stale_source.formations,
            decision_lab=DecisionLab().analyze(stale_source),
            recommendation_id="2-5-3",
        )

        self.assertIn("2-5-3", page._decision_lab_summary(result))
        self.assertEqual(page.decision_lab_rows(result)["formation"], "2-5-3")

    def test_show_results_normalizes_recommended_labels_from_identity(self):
        page = MatchPage()
        result = MatchAnalysisResult(
            player_count=2,
            opponent_name="Rival FC",
            players_csv_filename="players.csv",
            analyzed_formations=["3-5-2", "2-5-3"],
            completed_at="2026-07-15 10:00:00",
            recommendation_id="2-5-3",
            formations=[
                FormationAnalysisResult(
                    formation_name="3-5-2",
                    recommended_tactic="Normal",
                    tactic_level=0,
                    win_probability=0.61,
                    draw_probability=0.20,
                    loss_probability=0.19,
                    possession=0.55,
                    expected_goals=1.8,
                    opponent_expected_goals=0.9,
                    is_recommended=True,
                    lineup=[
                        LineupPlayerResult(1, "FORWARD", "CENTER", "NORMAL", "", "A")
                    ],
                ),
                FormationAnalysisResult(
                    formation_name="2-5-3",
                    recommended_tactic="Normal",
                    tactic_level=0,
                    win_probability=0.50,
                    draw_probability=0.25,
                    loss_probability=0.25,
                    possession=0.52,
                    expected_goals=1.4,
                    opponent_expected_goals=1.1,
                    is_recommended=False,
                    lineup=[
                        LineupPlayerResult(1, "FORWARD", "CENTER", "NORMAL", "", "B")
                    ],
                ),
            ],
        )

        page.show_results(result)

        self.assertEqual(page.recommended_rows(page._last_result), ["2-5-3"])
        labels = [
            page._formation_board_widget.formation_combo.itemText(index)
            for index in range(page._formation_board_widget.formation_combo.count())
        ]
        self.assertIn("2-5-3 (Recommended)", labels)
        self.assertIn("3-5-2 (Alternative)", labels)

    def test_formation_selector_presets(self):
        page = MatchPage()
        formations = [
            "2-5-3",
            "3-4-3",
            "3-5-2",
            "4-3-3",
            "4-4-2",
            "4-5-1",
            "5-2-3",
            "5-3-2",
            "5-4-1",
        ]

        page.set_supported_formations(
            formations,
            favorite_formations=["3-5-2", "4-5-1"]
        )

        page.select_all_formations()
        self.assertEqual(
            page.selected_formations(),
            formations
        )
        self.assertIn(
            "longer",
            page.formation_warning_label.text()
        )

        page.clear_all_formations()
        self.assertEqual(
            page.selected_formations(),
            []
        )

        page.select_favorite_formations()
        self.assertEqual(
            page.selected_formations(),
            ["3-5-2", "4-5-1"]
        )

    def test_formation_selector_applies_persisted_selection(self):
        page = MatchPage()
        page.set_supported_formations(
            ["2-5-3", "3-5-2", "4-5-1"]
        )
        page.apply_settings(
            MatchWorkspaceSettings(
                selected_formations=["2-5-3"]
            )
        )

        self.assertEqual(
            page.selected_formations(),
            ["2-5-3"]
        )


if __name__ == "__main__":
    unittest.main()
