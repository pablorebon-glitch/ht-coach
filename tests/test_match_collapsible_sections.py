import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceRepository,
    MatchWorkspaceSettings,
)
from ht_coach_app.reasoning.models import (
    ConfidenceAssessment,
    DecisionLabResult,
    DecisionReason,
    RecommendedDecision,
)
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
)
from ht_coach_app.ui.design_system.collapsible_section import CollapsibleSection
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.widgets.formation_board.formation_board import FormationBoard
from ht_coach_app.widgets.formation_board.formation_layouts import get_formation_layout


def formation_result(name="3-5-2", recommended=True):
    return FormationAnalysisResult(
        formation_name=name,
        recommended_tactic="Pressing",
        tactic_level=7.25,
        win_probability=0.55,
        draw_probability=0.25,
        loss_probability=0.20,
        possession=0.61,
        expected_goals=2.1,
        opponent_expected_goals=1.2,
        lineup=[
            LineupPlayerResult(
                number=index + 1,
                position=slot.position_label,
                side=slot.side,
                order="Normal",
                order_side="",
                player_name=f"Player {index + 1}",
            )
            for index, slot in enumerate(get_formation_layout(name))
        ],
        is_recommended=recommended,
    )


def decision_lab():
    return DecisionLabResult(
        recommended_formation=RecommendedDecision(
            formation="3-5-2",
            tactic="Pressing",
            win_probability=0.55,
            confidence="HIGH",
        ),
        headline="3-5-2 is recommended",
        summary="Decision Lab summary",
        confidence=ConfidenceAssessment(
            level="HIGH",
            score=0.9,
            explanation="Clear advantage.",
        ),
        confidence_score=0.9,
        reasons=[
            DecisionReason(
                code="win",
                title="Highest win probability",
                description="Best result among analyzed formations.",
                importance="high",
            )
        ],
    )


def match_result(with_decision_lab=True):
    return MatchAnalysisResult(
        player_count=22,
        opponent_name="Rival FC",
        formations=[
            formation_result("3-5-2", recommended=True),
            formation_result("4-5-1", recommended=False),
        ],
        players_csv_filename="players.csv",
        analyzed_formations=["3-5-2", "4-5-1"],
        completed_at="2026-07-21 12:00:00",
        decision_lab=decision_lab() if with_decision_lab else None,
    )


class MatchCollapsibleSectionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        configure_localization("en")

    def sections(self, page):
        return {
            section.state_key: section
            for section in page.findChildren(CollapsibleSection)
        }

    def test_all_match_sections_use_shared_collapsible_component(self):
        page = MatchPage()
        page.show_results(match_result())
        sections = self.sections(page)

        self.assertEqual(
            set(sections),
            {
                "decision_lab",
                "match_intelligence",
                "rating_calibration",
                "match_analysis",
            },
        )
        self.assertFalse(sections["decision_lab"].is_expanded())
        self.assertFalse(sections["rating_calibration"].is_expanded())
        self.assertTrue(sections["match_intelligence"].is_expanded())
        self.assertTrue(sections["match_analysis"].is_expanded())

    def test_header_arrow_enter_and_space_toggle_body_visibility(self):
        page = MatchPage()
        page.show_results(match_result())
        section = self.sections(page)["match_analysis"]

        QTest.mouseClick(section.header_button, Qt.LeftButton)
        self.assertFalse(section.is_expanded())
        self.assertTrue(section.body_host.isHidden())
        self.assertIsNotNone(section.body_widget())

        QTest.mouseClick(section.arrow_label, Qt.LeftButton)
        self.assertTrue(section.is_expanded())
        self.assertFalse(section.body_host.isHidden())

        section.header_button.setFocus()
        QTest.keyClick(section.header_button, Qt.Key_Return)
        self.assertFalse(section.is_expanded())

        QTest.keyClick(section.header_button, Qt.Key_Space)
        self.assertTrue(section.is_expanded())

    def test_section_state_is_independent_and_survives_refresh(self):
        page = MatchPage()
        page.show_results(match_result())
        sections = self.sections(page)
        sections["decision_lab"].set_expanded(True)
        sections["match_intelligence"].set_expanded(False)

        page.show_results(match_result())
        refreshed = self.sections(page)

        self.assertTrue(refreshed["decision_lab"].is_expanded())
        self.assertFalse(refreshed["match_intelligence"].is_expanded())
        self.assertFalse(refreshed["rating_calibration"].is_expanded())
        self.assertTrue(refreshed["match_analysis"].is_expanded())

    def test_collapsed_section_updates_without_auto_expanding(self):
        page = MatchPage()
        page.show_results(match_result(with_decision_lab=False))
        section = self.sections(page)["decision_lab"]
        section.set_expanded(False)

        page.show_results(match_result(with_decision_lab=True))
        updated = self.sections(page)["decision_lab"]

        self.assertFalse(updated.is_expanded())
        self.assertIn("Recommended: 3-5-2", updated.summary_label.text())
        labels = [
            label.text()
            for label in updated.body_widget().findChildren(QLabel)
        ]
        self.assertIn("Recommendation confidence: High", labels)

    def test_viewport_pitch_and_selection_survive_info_section_toggle(self):
        page = MatchPage()
        page.show_results(match_result())
        page.resize(1400, 900)
        page.show()
        QApplication.processEvents()

        scroll = page.findChild(QScrollArea, "matchPageScroll")
        scroll.verticalScrollBar().setValue(120)
        board = page.findChild(FormationBoard)
        first_player = board.current_board().slots[0].player.player_id
        board.select_player(first_player)
        before_pitch = board.pitch.pitch_rect().size()

        self.sections(page)["decision_lab"].toggle()
        QApplication.processEvents()

        self.assertEqual(board.pitch.pitch_rect().size(), before_pitch)
        self.assertEqual(board.current_board().selected_player_id, first_player)
        self.assertGreaterEqual(scroll.verticalScrollBar().value(), 0)

    def test_persisted_section_state_reloads_after_restart(self):
        temp_dir = tempfile.TemporaryDirectory()
        base = Path(temp_dir.name)
        repository = MatchWorkspaceRepository(
            base / "workspace.json",
            base / "result.json",
        )
        repository.save(
            MatchWorkspaceSettings(
                match_section_states={
                    "decision_lab": True,
                    "match_intelligence": False,
                    "rating_calibration": True,
                    "match_analysis": False,
                }
            )
        )

        page = MatchPage()
        page.apply_settings(repository.load())
        page.show_results(match_result())
        states = page.match_section_states()

        self.assertTrue(states["decision_lab"])
        self.assertFalse(states["match_intelligence"])
        self.assertTrue(states["rating_calibration"])
        self.assertFalse(states["match_analysis"])
        temp_dir.cleanup()

    def test_english_and_spanish_headers_are_localized_without_raw_keys(self):
        page = MatchPage()
        page.show_results(match_result())
        english = [
            section.title_label.text()
            for section in self.sections(page).values()
        ]
        self.assertIn("Match Analysis", english)
        self.assertNotIn("match.match_analysis", english)

        configure_localization("es")
        page.retranslate_ui()
        spanish = [
            section.title_label.text()
            for section in self.sections(page).values()
        ]

        self.assertIn("Analisis del partido", spanish)
        self.assertIn("Inteligencia de partido", spanish)
        self.assertFalse(any("." in title for title in spanish))


if __name__ == "__main__":
    unittest.main()
