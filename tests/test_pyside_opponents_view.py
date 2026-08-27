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

    def test_opponents_page_places_list_and_detail_actions(self):
        page = OpponentsPage()

        self.assertIs(
            page.delete_button.parent(),
            page.list_actions_widget
        )
        self.assertIs(
            page.move_up_button.parent(),
            page.list_actions_widget
        )
        self.assertIs(
            page.move_down_button.parent(),
            page.list_actions_widget
        )
        self.assertIs(
            page.new_button.parent(),
            page.details_actions_widget
        )
        self.assertIs(
            page.paste_ratings_button.parent(),
            page.details_actions_widget
        )
        self.assertIs(
            page.save_button.parent(),
            page.details_actions_widget
        )
        self.assertFalse(
            hasattr(page, "duplicate_button")
        )

    def test_opponents_page_reorder_buttons_follow_selection_boundaries(self):
        from models.opponent import Opponent
        from models.team_ratings import TeamRatings

        page = OpponentsPage()
        page.set_opponents(
            [
                Opponent("Alpha", TeamRatings()),
                Opponent("Bravo", TeamRatings()),
                Opponent("Charlie", TeamRatings()),
            ],
            selected_name="Alpha",
        )

        self.assertFalse(page.move_up_button.isEnabled())
        self.assertTrue(page.move_down_button.isEnabled())

        page.opponent_list.setCurrentRow(1)
        self.assertTrue(page.move_up_button.isEnabled())
        self.assertTrue(page.move_down_button.isEnabled())

        page.opponent_list.setCurrentRow(2)
        self.assertTrue(page.move_up_button.isEnabled())
        self.assertFalse(page.move_down_button.isEnabled())

    def test_opponents_page_new_clears_selection_and_disables_list_actions(self):
        from models.opponent import Opponent
        from models.team_ratings import TeamRatings
        from ht_coach_app.services.opponent_service import DEFAULT_RATINGS

        page = OpponentsPage()
        page.set_opponents(
            [Opponent("Alpha", TeamRatings())],
            selected_name="Alpha",
        )

        page.clear_editor(DEFAULT_RATINGS)

        self.assertIsNone(page.selected_opponent_name())
        self.assertFalse(page.delete_button.isEnabled())
        self.assertFalse(page.move_up_button.isEnabled())
        self.assertFalse(page.move_down_button.isEnabled())


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
                                position="Goalkeeper (GK)",
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
