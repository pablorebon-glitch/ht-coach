import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from engine.match_intelligence import MatchIntelligenceEngine
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
    SectorRatingComparisonResult,
    TeamRatingsResult,
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
        team_ratings=TeamRatingsResult(
            left_defense=35,
            central_defense=40,
            right_defense=45,
            midfield=42,
            left_attack=34,
            central_attack=39,
            right_attack=31,
        ),
        opponent_ratings=TeamRatingsResult(
            left_defense=31,
            central_defense=35,
            right_defense=29,
            midfield=38,
            left_attack=41,
            central_attack=33,
            right_attack=28,
        ),
        sector_rating_comparisons=[
            SectorRatingComparisonResult(
                matchup_key="midfield",
                our_sector="midfield",
                opponent_sector="midfield",
                our_value=42,
                opponent_value=38,
                our_scale="ht_coach_internal_contribution",
                opponent_scale="ht_coach_internal_contribution",
                difference=4,
                advantage="ours",
                comparable=True,
            )
        ],
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


def rich_match_result():
    result = match_result(with_decision_lab=True)
    return replace(
        result,
        match_intelligence=MatchIntelligenceEngine().analyze(result),
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

    def show_page(self, page, width=1366, height=900):
        page.resize(width, height)
        page.show()
        QApplication.processEvents()

    def layout_widgets(self, page):
        return [
            page.results_layout.itemAt(index).widget()
            for index in range(page.results_layout.count())
            if page.results_layout.itemAt(index).widget() is not None
        ]

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
        self.assertFalse(sections["match_intelligence"].is_expanded())
        self.assertTrue(sections["match_analysis"].is_expanded())

    def test_expanded_match_section_bodies_are_visible_and_populated(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page)
        sections = self.sections(page)

        expected_text = {
            "decision_lab": "Recommendation confidence",
            "match_intelligence": "Tactical Focus",
            "rating_calibration": "Opponent Rating Calibration",
            "match_analysis": "Recommended",
        }
        for key, text in expected_text.items():
            section = sections[key]
            section.set_expanded(True)
            QApplication.processEvents()

            labels = [
                label.text()
                for label in section.body_widget().findChildren(QLabel)
            ]
            self.assertFalse(section.body_host.isHidden(), key)
            self.assertFalse(section.body_widget().isHidden(), key)
            self.assertGreater(section.body_host.height(), 0, key)
            self.assertGreater(section.body_widget().sizeHint().height(), 0, key)
            self.assertTrue(any(text in label for label in labels), key)

            section.set_expanded(False)
            QApplication.processEvents()
            self.assertTrue(section.body_host.isHidden(), key)
            self.assertEqual(section.body_host.maximumHeight(), 0, key)

    def test_match_accordion_stack_order_places_workspace_after_sections(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        sections = self.sections(page)
        for section in sections.values():
            section.set_expanded(False)
        self.show_page(page)

        widgets = self.layout_widgets(page)
        self.assertEqual(
            [widget.state_key for widget in widgets[:4]],
            [
                "decision_lab",
                "match_intelligence",
                "rating_calibration",
                "match_analysis",
            ],
        )
        self.assertIsInstance(widgets[4], QTabWidget)
        self.assertEqual(widgets[4].objectName(), "matchResultTabs")
        self.assertTrue(page.results_layout.itemAt(5).spacerItem() is not None)

    def test_collapsed_headers_are_consecutive_and_workspace_follows(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        sections_by_key = self.sections(page)
        sections = [
            sections_by_key[key]
            for key in (
                "decision_lab",
                "match_intelligence",
                "rating_calibration",
                "match_analysis",
            )
        ]
        for section in sections:
            section.set_expanded(False)
        self.show_page(page)

        for index in range(len(sections) - 1):
            bottom = sections[index].mapTo(
                page,
                sections[index].rect().bottomLeft(),
            ).y()
            next_top = sections[index + 1].mapTo(
                page,
                sections[index + 1].rect().topLeft(),
            ).y()
            self.assertLessEqual(next_top - bottom, 12)

        workspace = page.findChild(QTabWidget, "matchResultTabs")
        analysis_bottom = sections[-1].mapTo(
            page,
            sections[-1].rect().bottomLeft(),
        ).y()
        workspace_top = workspace.mapTo(page, workspace.rect().topLeft()).y()
        self.assertLessEqual(workspace_top - analysis_bottom, 12)

    def test_match_analysis_returns_below_calibration_after_collapse(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page)
        sections = self.sections(page)
        analysis = sections["match_analysis"]
        calibration = sections["rating_calibration"]

        analysis.set_expanded(True)
        QApplication.processEvents()
        analysis.set_expanded(False)
        QApplication.processEvents()

        calibration_bottom = calibration.mapTo(
            page,
            calibration.rect().bottomLeft(),
        ).y()
        analysis_top = analysis.mapTo(page, analysis.rect().topLeft()).y()
        self.assertLessEqual(analysis_top - calibration_bottom, 12)
        self.assertTrue(analysis.body_host.isHidden())

    def test_one_expanded_section_inserts_only_its_body_height(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        sections = self.sections(page)
        for section in sections.values():
            section.set_expanded(False)
        self.show_page(page)
        workspace = page.findChild(QTabWidget, "matchResultTabs")
        collapsed_top = workspace.mapTo(page, workspace.rect().topLeft()).y()

        decision = sections["decision_lab"]
        decision.set_expanded(True)
        QApplication.processEvents()
        expanded_top = workspace.mapTo(page, workspace.rect().topLeft()).y()

        inserted = expanded_top - collapsed_top
        self.assertGreater(inserted, decision.body_widget().sizeHint().height() - 12)
        self.assertLess(inserted, decision.body_widget().sizeHint().height() + 36)

    def test_each_section_survives_ten_toggle_cycles_without_height_growth(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page)
        sections = self.sections(page)

        for key, section in sections.items():
            collapsed_heights = []
            for _ in range(10):
                section.set_expanded(False)
                QApplication.processEvents()
                collapsed_heights.append(section.sizeHint().height())
                section.set_expanded(True)
                QApplication.processEvents()
            self.assertTrue(section.is_expanded(), key)
            self.assertFalse(section.body_host.isHidden(), key)
            self.assertGreater(section.body_host.height(), 0, key)
            self.assertLessEqual(
                max(collapsed_heights) - min(collapsed_heights),
                2,
                key,
            )

    def test_mixed_section_cycles_keep_stack_compact(self):
        page = MatchPage()
        page.show_results(rich_match_result())
        self.show_page(page)
        sections = self.sections(page)

        sections["decision_lab"].set_expanded(True)
        sections["match_intelligence"].set_expanded(True)
        sections["decision_lab"].set_expanded(False)
        sections["rating_calibration"].set_expanded(True)
        sections["match_intelligence"].set_expanded(False)
        sections["match_analysis"].set_expanded(True)
        for section in sections.values():
            section.set_expanded(False)
        QApplication.processEvents()

        ordered = [
            sections[key]
            for key in (
                "decision_lab",
                "match_intelligence",
                "rating_calibration",
                "match_analysis",
            )
        ]
        for index in range(len(ordered) - 1):
            bottom = ordered[index].mapTo(
                page,
                ordered[index].rect().bottomLeft(),
            ).y()
            next_top = ordered[index + 1].mapTo(
                page,
                ordered[index + 1].rect().topLeft(),
            ).y()
            self.assertLessEqual(next_top - bottom, 12)

        for section in ordered:
            section.set_expanded(True)
            QApplication.processEvents()
            self.assertFalse(section.body_host.isHidden(), section.state_key)
            self.assertGreater(section.body_host.height(), 0, section.state_key)
            section.set_expanded(False)

    def test_refresh_while_each_section_collapsed_preserves_position_and_updates_body(self):
        for key in (
            "decision_lab",
            "match_intelligence",
            "rating_calibration",
            "match_analysis",
        ):
            page = MatchPage()
            page.show_results(rich_match_result())
            self.show_page(page)
            sections = self.sections(page)
            section = sections[key]
            section.set_expanded(False)
            QApplication.processEvents()
            before_top = section.mapTo(page, section.rect().topLeft()).y()

            page.show_results(rich_match_result())
            QApplication.processEvents()

            refreshed = self.sections(page)[key]
            after_top = refreshed.mapTo(page, refreshed.rect().topLeft()).y()
            self.assertFalse(refreshed.is_expanded(), key)
            self.assertTrue(refreshed.body_host.isHidden(), key)
            self.assertLessEqual(abs(after_top - before_top), 8, key)

            refreshed.set_expanded(True)
            QApplication.processEvents()
            self.assertFalse(refreshed.body_host.isHidden(), key)
            self.assertGreater(refreshed.body_host.height(), 0, key)

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

    def test_collapsed_size_hint_uses_header_height_only(self):
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.addWidget(QLabel("Tall body\n" * 40))
        section = CollapsibleSection(
            "Section",
            body,
            state_key="geometry",
            expanded=True,
            summary="Summary",
        )
        expanded_height = section.sizeHint().height()

        section.set_expanded(False)
        QApplication.processEvents()

        self.assertLess(section.sizeHint().height(), expanded_height)
        self.assertLessEqual(
            abs(
                section.sizeHint().height()
                - section.header_button.sizeHint().height()
            ),
            6,
        )
        self.assertTrue(section.body_host.isHidden())
        self.assertFalse(section.body_widget().isVisible())
        self.assertEqual(
            section.body_host.sizePolicy().verticalPolicy(),
            QSizePolicy.Policy.Ignored,
        )
        self.assertEqual(section.body_host.maximumHeight(), 0)

        section.set_expanded(True)
        QApplication.processEvents()

        self.assertGreater(section.sizeHint().height(), section.header_button.sizeHint().height())
        self.assertEqual(
            section.body_host.sizePolicy().verticalPolicy(),
            QSizePolicy.Policy.Preferred,
        )
        self.assertGreater(section.body_host.maximumHeight(), 0)

    def test_dynamic_body_size_changes_are_reflected_when_expanded(self):
        body = QWidget()
        layout = QVBoxLayout(body)
        dynamic = QLabel("Short body")
        layout.addWidget(dynamic)
        section = CollapsibleSection("Section", body, state_key="dynamic")
        section.show()
        QApplication.processEvents()
        before = section.sizeHint().height()

        dynamic.setMinimumHeight(dynamic.minimumHeight() + 120)
        layout.invalidate()
        section.layout().invalidate()
        body.updateGeometry()
        section.updateGeometry()
        QApplication.processEvents()

        self.assertGreater(section.sizeHint().height(), before)

    def test_repeated_toggles_are_stable_and_keep_body_instance(self):
        body = QLabel("Persistent body\n" * 8)
        section = CollapsibleSection("Section", body, state_key="repeat")

        for _ in range(5):
            section.set_expanded(False)
            QApplication.processEvents()
            self.assertIs(section.body_widget(), body)
            self.assertTrue(section.body_host.isHidden())
            self.assertEqual(section.header_button.accessibleDescription(), "collapsed")
            section.set_expanded(True)
            QApplication.processEvents()
            self.assertIs(section.body_widget(), body)
            self.assertFalse(section.body_host.isHidden())
            self.assertEqual(section.header_button.accessibleDescription(), "expanded")

        self.assertGreater(
            section.sizeHint().height(),
            section.header_button.sizeHint().height(),
        )

    def test_toggle_does_not_emit_match_recalculate_signal(self):
        page = MatchPage()
        page.show_results(match_result())
        calls = []
        page.workspace_recalculate_requested.connect(calls.append)

        self.sections(page)["match_analysis"].toggle()
        QApplication.processEvents()

        self.assertEqual(calls, [])

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

    def test_match_sections_have_no_stretch_between_headers(self):
        page = MatchPage()
        page.show_results(match_result())
        sections = self.sections(page)
        for section in sections.values():
            section.set_expanded(False)
        QApplication.processEvents()

        layout = page.results_layout
        section_items = [layout.itemAt(index) for index in range(4)]

        self.assertEqual(
            [
                item.widget().state_key
                for item in section_items
            ],
            [
                "decision_lab",
                "match_intelligence",
                "rating_calibration",
                "match_analysis",
            ],
        )
        self.assertIsInstance(layout.itemAt(4).widget(), QTabWidget)
        self.assertTrue(layout.itemAt(5).spacerItem() is not None)
        for index in range(4):
            self.assertEqual(layout.stretch(index), 0)
            self.assertIsNotNone(layout.itemAt(index).widget())
        self.assertEqual(layout.stretch(4), 0)

    def test_collapsed_match_sections_stack_with_natural_height(self):
        page = MatchPage()
        page.show_results(match_result())
        page.resize(1366, 768)
        page.show()
        sections = [
            self.sections(page)[key]
            for key in (
                "decision_lab",
                "match_intelligence",
                "rating_calibration",
                "match_analysis",
            )
        ]
        for section in sections:
            section.set_expanded(False)
        QApplication.processEvents()

        bottoms_and_tops = [
            (
                sections[index].mapTo(page, sections[index].rect().bottomLeft()).y(),
                sections[index + 1].mapTo(page, sections[index + 1].rect().topLeft()).y(),
            )
            for index in range(len(sections) - 1)
        ]

        for bottom, next_top in bottoms_and_tops:
            self.assertLessEqual(next_top - bottom, 12)

    def test_expanding_small_section_grows_only_by_body_height(self):
        page = MatchPage()
        page.show_results(match_result(with_decision_lab=False))
        section = self.sections(page)["decision_lab"]
        section.set_expanded(False)
        QApplication.processEvents()
        collapsed = section.sizeHint().height()

        section.set_expanded(True)
        QApplication.processEvents()
        expanded = section.sizeHint().height()

        self.assertGreater(expanded, collapsed)
        self.assertLess(expanded - collapsed, 180)

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

    def test_repeated_toggle_and_refresh_preserves_collapsed_geometry(self):
        page = MatchPage()
        page.show_results(match_result())
        page.resize(1366, 768)
        page.show()
        QApplication.processEvents()
        sections = self.sections(page)
        section = sections["match_analysis"]
        collapsed_heights = []

        for _ in range(4):
            section.set_expanded(False)
            QApplication.processEvents()
            collapsed_heights.append(section.sizeHint().height())
            page.show_results(match_result())
            section = self.sections(page)["match_analysis"]
            self.assertFalse(section.is_expanded())
            self.assertTrue(section.body_host.isHidden())
            self.assertEqual(section.body_host.maximumHeight(), 0)
            self.assertEqual(
                section.body_host.sizePolicy().verticalPolicy(),
                QSizePolicy.Policy.Ignored,
            )
            section.set_expanded(True)
            QApplication.processEvents()
            self.assertFalse(section.body_host.isHidden())
            self.assertGreater(section.body_host.maximumHeight(), 0)

        section.set_expanded(False)
        QApplication.processEvents()
        collapsed_heights.append(section.sizeHint().height())
        self.assertLessEqual(max(collapsed_heights) - min(collapsed_heights), 2)

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

        self.sections(page)["decision_lab"].toggle()
        QApplication.processEvents()

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
