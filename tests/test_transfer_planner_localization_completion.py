import unittest
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from engine.squad_evolution.models import (
    HORIZON_MEDIUM_TERM,
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    SUCCESSION_NONE,
    DependencyResult,
    IdentityContinuityResult,
    SquadEvolutionResult,
    SuccessionMapRow,
    TrainingAlignmentResult,
)
from engine.transfer_planner.planner import TransferPlanner
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.transfer_planner_presenter import (
    TransferPlannerPresenter,
)
from ht_coach_app.views.squad_page import SquadPage
from PySide6.QtWidgets import QApplication


class TransferPlannerLocalizationCompletionTest(unittest.TestCase):
    def setUp(self):
        configure_localization("es")
        self.page = SquadPage.__new__(SquadPage)

    def tearDown(self):
        configure_localization("en")

    def test_domain_literals_are_localized_for_spanish_transfer_view(self):
        examples = [
            ("role", "Central Defense", "Defensa central"),
            ("position", "Inner Midfielder", "Mediocampista central"),
            ("target_role", "Immediate Starter", "Titular inmediato"),
            ("specialty", "Header preferred", "Cabeceador preferido"),
            ("formation", "All supported formations", "Todas las formaciones soportadas"),
            ("impact_dimension", "Succession Risk", "Riesgo de sucesion"),
            (
                "tradeoff",
                "May not align strongly with the current training focus.",
                "Puede no alinearse fuerte con el entrenamiento actual.",
            ),
            (
                "no_action",
                "Coverage appears adequate today.",
                "La cobertura parece adecuada hoy.",
            ),
        ]

        for category, raw, expected in examples:
            with self.subTest(category=category):
                self.assertEqual(self.presenter().translate_literal(category, raw), expected)

    def test_transfer_summary_replaces_engine_sentences_with_localized_text(self):
        summary = SimpleNamespace(top_priority="Forward")

        lines = self.presenter().summary_sentences(summary)

        self.assertEqual(
            lines,
            [
                "La prioridad principal de fichaje es Delantero.",
                "Las recomendaciones se basan en perfiles y no usan datos de mercado en vivo.",
            ],
        )

    def test_unknown_transfer_literals_fall_back_to_readable_title_case(self):
        self.assertEqual(
            self.presenter().translate_literal("role", "custom_role"),
            "Custom Role",
        )

    def test_missing_transfer_skill_does_not_show_translation_unavailable(self):
        self.assertEqual(
            self.presenter().translate_skill("unknown_skill"),
            "Unknown Skill",
        )

    def test_spanish_list_formatting_uses_spanish_conjunction(self):
        text = self.presenter().format_list(
            ["Jugadas", "Pases", "Balon parado"]
        )

        self.assertEqual(text, "Jugadas, Pases y Balon parado")

    def test_spanish_profile_contains_no_english_domain_values(self):
        result = transfer_plan_result()
        text = self.presenter().need_presentation(result.needs[0])
        rendered = "\n".join(
            [
                text.summary,
                text.profile,
                text.why,
                text.impact,
                text.no_action,
                text.alternatives,
                text.technical,
            ]
        )

        forbidden = [
            "Central Defender",
            "Rotation Player",
            "Reliable Backup",
            "Development Prospect",
            "Playmaking",
            "Passing",
            "Set Pieces",
            "Neutral",
            "Succession Risk",
            "Current Coverage",
            "Formation Flexibility",
            "Training Pipeline",
            "Buy Now",
            "Translation unavailable",
            "transfer.",
        ]
        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, rendered)

    def test_english_output_remains_readable(self):
        configure_localization("en")
        result = transfer_plan_result()
        text = self.presenter().need_presentation(result.needs[0])

        self.assertIn("Position:", text.summary)
        self.assertIn("Buy Now", text.summary)
        self.assertIn("Primary skill", text.profile)
        self.assertIn("Defending", text.profile)
        self.assertIn("If No Action", t_section_title("no_action"))

    @staticmethod
    def presenter():
        return TransferPlannerPresenter()


class TransferPlannerStructuredViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        configure_localization("es")
        self.page = SquadPage()
        self.result = transfer_plan_result()
        self.page.show_transfer_plan(self.result)

    def tearDown(self):
        configure_localization("en")

    def test_detail_panel_has_semantic_sections(self):
        self.assertEqual(
            set(self.page.transfer_detail_sections),
            {
                "summary",
                "profile",
                "why",
                "impact",
                "no_action",
                "alternatives",
                "technical",
            },
        )
        self.assertIn("Resumen de recomendacion", self.section_title("summary"))
        self.assertIn("Perfil recomendado", self.section_title("profile"))
        self.assertIn("Por que incorporar", self.section_title("why"))
        self.assertIn("Impacto esperado", self.section_title("impact"))
        self.assertIn("Si no se actua", self.section_title("no_action"))

    def test_priority_table_is_localized_and_has_tooltips(self):
        values = [
            self.page.transfer_priority_table.item(0, column).text()
            for column in range(self.page.transfer_priority_table.columnCount())
        ]

        self.assertIn("Defensa central", values)
        self.assertIn("Comprar ahora", values)
        self.assertNotIn("Central Defense", values)
        self.assertNotIn("Buy Now", values)
        self.assertEqual(
            self.page.transfer_priority_table.item(0, 1).toolTip(),
            self.page.transfer_priority_table.item(0, 1).text(),
        )

    def test_alternative_profiles_are_structured(self):
        text = self.page.transfer_alternatives_label.text()

        self.assertIn("Alternativa 1", text)
        self.assertIn("Rango de edad:", text)
        self.assertIn("Habilidad principal:", text)
        self.assertNotIn("Reliable Backup:", text)

    def test_selection_refreshes_sections_and_resets_scroll(self):
        self.page.transfer_detail_scroll.verticalScrollBar().setValue(100)
        self.page.transfer_priority_table.selectRow(1)
        QApplication.processEvents()

        self.assertEqual(
            self.page.transfer_detail_scroll.verticalScrollBar().value(),
            0,
        )
        self.assertTrue(self.page.transfer_summary_detail_label.text())

    def test_language_switch_preserves_selection_without_analysis_rerun(self):
        self.page.transfer_priority_table.selectRow(1)
        selected_need = self.page._transfer_needs[1].need_id

        configure_localization("en")
        self.page.retranslate_ui()

        selected = self.page.transfer_priority_table.selectedItems()
        self.assertTrue(selected)
        self.assertEqual(
            self.page._transfer_needs[selected[0].row()].need_id,
            selected_need,
        )
        self.assertIn("Recommendation Summary", self.section_title("summary"))
        self.assertIn("Monitor", self.page.transfer_summary_detail_label.text())

    def test_empty_technical_section_is_hidden_without_stale_text(self):
        need = self.result.needs[0]
        if not need.data_limitations and not need.confidence_reasons:
            self.assertEqual(self.page.transfer_technical_label.text(), "")
            self.assertFalse(self.page.transfer_detail_sections["technical"].isVisible())

    def section_title(self, key):
        return self.page.transfer_detail_sections[key].title_label.text()


def transfer_plan_result():
    return TransferPlanner().build_plan(
        SquadEvolutionResult(
            planning_horizon=HORIZON_MEDIUM_TERM,
            succession_map=(
                SuccessionMapRow(
                    role="Central Defense",
                    full_strength_starter="Veteran Defender",
                    current_available_starter="Veteran Defender",
                    primary_backup="",
                    potential_successor="",
                    starter_age_band="veteran",
                    current_depth=1,
                    succession_readiness=SUCCESSION_NONE,
                    operational_risk=RISK_HIGH,
                    structural_risk=RISK_CRITICAL,
                    temporary_issue=False,
                    structural_gap=True,
                    explanation="Central Defense test risk",
                ),
                SuccessionMapRow(
                    role="Forward",
                    full_strength_starter="Forward Starter",
                    current_available_starter="Forward Starter",
                    primary_backup="",
                    potential_successor="",
                    starter_age_band="prime",
                    current_depth=1,
                    succession_readiness=SUCCESSION_NONE,
                    operational_risk=RISK_HIGH,
                    structural_risk=RISK_LOW,
                    temporary_issue=True,
                    structural_gap=False,
                    explanation="Forward test risk",
                ),
            ),
            dependencies=(
                DependencyResult(
                    key_player="Veteran Defender",
                    role="Central Defense",
                    dependency_level=RISK_CRITICAL,
                    current_impact="High",
                    structural_impact="High",
                    successor_status="No successor",
                    reason="Single point of failure",
                ),
            ),
            training_alignment=TrainingAlignmentResult(
                current_training="playmaking",
                strongly_supports=("Midfield",),
                not_addressed=("Central Defense",),
            ),
            identity_continuity=IdentityContinuityResult(
                current_identity="Defensive Squad",
                continuity="watch",
                reason="Test identity",
                key_contributors=("Veteran Defender",),
            ),
        )
    )


def t_section_title(key):
    from ht_coach_app.core.localization import t

    return t(f"transfer.section.{key}")


if __name__ == "__main__":
    unittest.main()
