import unittest
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ht_coach_app.core.localization import configure_localization
from ht_coach_app.views.squad_page import SquadPage


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
                self.assertEqual(
                    SquadPage._transfer_literal(self.page, category, raw),
                    expected,
                )

    def test_transfer_summary_replaces_engine_sentences_with_localized_text(self):
        summary = SimpleNamespace(top_priority="Forward")

        lines = SquadPage._transfer_summary_sentences(self.page, summary)

        self.assertEqual(
            lines,
            [
                "La prioridad principal de fichaje es Delantero.",
                "Las recomendaciones se basan en perfiles y no usan datos de mercado en vivo.",
            ],
        )

    def test_unknown_transfer_literals_fall_back_to_readable_title_case(self):
        self.assertEqual(
            SquadPage._transfer_literal(self.page, "role", "custom_role"),
            "Custom Role",
        )

    def test_missing_transfer_skill_does_not_show_translation_unavailable(self):
        self.assertEqual(
            SquadPage._transfer_skill(self.page, "unknown_skill"),
            "Unknown Skill",
        )


if __name__ == "__main__":
    unittest.main()
