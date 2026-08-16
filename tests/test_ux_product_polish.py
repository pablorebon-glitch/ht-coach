import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceRepository,
    MatchWorkspaceSettings,
)
from ht_coach_app.services.opponent_service import HATTRICK_SECTOR_ORDER
from ht_coach_app.ui.design_system.badges import StatusBadge
from ht_coach_app.ui.design_system.cards import Card
from ht_coach_app.ui.design_system.colors import STATUS_COLORS
from ht_coach_app.ui.design_system.empty_state import EmptyState
from ht_coach_app.ui.design_system.section_header import SectionHeader
from ht_coach_app.ui.design_system.status import (
    SEMANTIC_STATUSES,
    display_unknown,
    normalize_status,
)
from ht_coach_app.ui.design_system.styles import application_stylesheet
from ht_coach_app.ui.design_system.tables import configure_table
from ht_coach_app.views.base_page import BasePage
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.views.opponents_page import OpponentsPage
from ht_coach_app.views.squad_page import SquadPage


class UXProductPolishTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(application_stylesheet())

    def test_design_tokens_cover_every_semantic_status(self):
        self.assertEqual(set(SEMANTIC_STATUSES), set(STATUS_COLORS))
        self.assertEqual(normalize_status("ready"), "positive")
        self.assertEqual(normalize_status("injured"), "unavailable")
        self.assertEqual(normalize_status("missing"), "unknown")
        self.assertEqual(display_unknown(""), "Unknown")

    def test_status_badge_pairs_text_with_semantic_state(self):
        badge = StatusBadge(
            "critical",
            "Critical",
            accessible_description="Critical transfer urgency",
        )

        self.assertEqual(badge.property("semanticStatus"), "critical")
        self.assertIn("Critical", badge.text())
        self.assertEqual(badge.accessibleName(), "Critical transfer urgency")

    def test_shared_card_header_and_empty_state_render(self):
        card = Card("warning", selected=True)
        header = SectionHeader("Transfer Plan", "Profiles only")
        empty = EmptyState("No squad analysis", "Import a squad file first.")

        card.layout.addWidget(header)
        card.layout.addWidget(empty)

        self.assertEqual(card.objectName(), "dsCard")
        self.assertEqual(card.property("variant"), "warning")
        self.assertEqual(header.title_label.text(), "Transfer Plan")
        self.assertEqual(empty.title_label.text(), "No squad analysis")

    def test_configure_table_standardizes_table_behavior(self):
        table = QTableWidget(1, 2)
        table.setHorizontalHeaderLabels(["Name", "Score"])
        configure_table(table, numeric_columns={1})
        table.setItem(0, 0, QTableWidgetItem("Player"))
        table.setItem(0, 1, QTableWidgetItem("10.5"))

        self.assertTrue(table.alternatingRowColors())
        self.assertFalse(table.verticalHeader().isVisible())
        self.assertGreaterEqual(table.verticalHeader().defaultSectionSize(), 24)

    def test_base_page_source_indicator_is_semantic_and_optional(self):
        page = BasePage("Squad", "Review roster")

        self.assertTrue(page.page_source_label.isHidden())
        page.set_source_indicator("players.csv", "neutral")

        self.assertFalse(page.page_source_label.isHidden())
        self.assertEqual(page.page_source_label.text(), "players.csv")
        self.assertEqual(page.page_source_label.property("semanticStatus"), "neutral")

    def test_squad_page_preserves_tab_key_and_shows_transfer_badges(self):
        page = SquadPage()

        page.set_selected_tab("transfer")

        self.assertEqual(page.selected_tab_key(), "transfer")
        self.assertEqual(page._risk_status("critical"), "critical")
        self.assertEqual(page._action_status("buy_now"), "critical")
        self.assertEqual(page._action_status("develop_internally"), "positive")

    def test_squad_page_keeps_only_practical_player_filters(self):
        page = SquadPage()

        page.search_edit.setText("ignored")
        page.minimum_form.setValue(7)
        page.minimum_stamina.setValue(8)
        page.training_fit_filter_combo.setCurrentIndex(
            max(0, page.training_fit_filter_combo.findData("excellent"))
        )
        values = page.filter_values()

        self.assertEqual(values["search_text"], "")
        self.assertEqual(values["minimum_form"], 0)
        self.assertEqual(values["minimum_stamina"], 0)
        self.assertEqual(values["training_fit"], "all")
        self.assertFalse(page.role_filter_combo.isHidden())
        self.assertFalse(page.status_filter_combo.isHidden())
        self.assertFalse(page.speciality_combo.isHidden())
        self.assertTrue(page.search_edit.isHidden())
        self.assertTrue(page.minimum_form.isHidden())
        self.assertTrue(page.minimum_stamina.isHidden())

    def test_match_empty_state_uses_shared_component(self):
        page = MatchPage()

        empty_states = page.findChildren(EmptyState)

        self.assertTrue(empty_states)
        self.assertEqual(empty_states[0].title_label.text(), "No analysis yet")

    def test_opponents_page_uses_localized_copy_and_panel_styles(self):
        page = OpponentsPage()

        self.assertEqual(page.page_title_label.text(), "Opponents")
        self.assertEqual(page.name_input.placeholderText(), "Opponent name")
        self.assertEqual(page._build_list_panel().objectName(), "workspacePanel")
        self.assertEqual(page.ratings_grid.rating_order(), HATTRICK_SECTOR_ORDER)
        self.assertEqual(page.paste_ratings_button.text(), "Paste Ratings")
        self.assertEqual(
            page.paste_ratings_button.accessibleName(),
            "Paste Ratings",
        )
        self.assertTrue(page.paste_ratings_button.toolTip())

    def test_workspace_settings_persist_selected_squad_tab(self):
        path = Path(os.environ.get("TEMP", ".")) / "ht_coach_ux_settings.json"
        if path.exists():
            path.unlink()
        repository = MatchWorkspaceRepository(path)
        repository.save(MatchWorkspaceSettings(squad_selected_tab="transfer"))

        self.assertEqual(repository.load().squad_selected_tab, "transfer")

        path.unlink(missing_ok=True)

    def test_localization_catalogs_have_no_duplicate_keys(self):
        for path in [
            Path("resources/i18n/en.json"),
            Path("resources/i18n/es.json"),
        ]:
            duplicates = []

            def hook(pairs):
                seen = set()
                for key, value in pairs:
                    if key in seen:
                        duplicates.append(key)
                    seen.add(key)
                return dict(pairs)

            json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=hook)
            self.assertEqual(duplicates, [], str(path))

    def test_temporary_pytest_directories_are_ignored(self):
        ignore_text = Path(".gitignore").read_text(encoding="utf-8")

        self.assertIn(".pytest_cache/", ignore_text)
        self.assertIn(".tmp_pytest*/", ignore_text)
