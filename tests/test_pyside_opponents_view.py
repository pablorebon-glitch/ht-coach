import unittest
import os


os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)


try:
    from PySide6.QtWidgets import QApplication

    from ht_coach_app.views.opponents_page import OpponentsPage
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QApplication = None
    OpponentsPage = None


@unittest.skipIf(
    QApplication is None,
    "PySide6 is not installed"
)
class OpponentsPageSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_opponents_page_can_be_constructed(self):
        page = OpponentsPage()

        self.assertEqual(
            page.current_opponent_name(),
            None
        )
        self.assertIsNotNone(
            page.ratings_grid
        )


class MatchPageSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QApplication is not None:
            cls.app = QApplication.instance() or QApplication([])

    @unittest.skipIf(
        OpponentsPage is None,
        "PySide6 is not installed"
    )
    def test_match_page_formats_results_deterministically(self):
        from ht_coach_app.services.match_workspace_service import (
            FormationAnalysisResult,
            LineupPlayerResult,
            MatchAnalysisResult,
        )
        from ht_coach_app.views.match_page import MatchPage

        page = MatchPage()
        page.set_supported_formations(
            ["3-5-2", "4-5-1"]
        )
        page.show_results(
            MatchAnalysisResult(
                player_count=2,
                opponent_name="Rival FC",
                formations=[
                    FormationAnalysisResult(
                        formation_name="3-5-2",
                        recommended_tactic="Pressing",
                        tactic_level=7.25,
                        win_probability=0.5,
                        draw_probability=0.3,
                        loss_probability=0.2,
                        possession=0.61,
                        expected_goals=2.1,
                        opponent_expected_goals=1.2,
                        lineup=[
                            LineupPlayerResult(
                                number=1,
                                position="GOALKEEPER",
                                side="CENTER",
                                order="Normal",
                                order_side="",
                                player_name="Keeper"
                            )
                        ],
                        is_recommended=True
                    )
                ]
            )
        )

        self.assertEqual(
            page._format_percent(0.615),
            "61.5%"
        )
        self.assertGreater(
            page.results_layout.count(),
            1
        )


if __name__ == "__main__":
    unittest.main()
