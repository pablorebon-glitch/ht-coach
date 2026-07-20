import json
import re
import unittest
from pathlib import Path

from engine.advisor.recommendation import Recommendation
from engine.advisor.recommendation_types import (
    RecommendationCardType,
    RecommendationCategory,
    RecommendationConfidence,
)
from ht_coach_app.core.localization import (
    TRANSLATION_UNAVAILABLE,
    LocalizationService,
    configure_localization,
)
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    TeamRatingsResult,
)

try:
    from PySide6.QtWidgets import QApplication, QLabel
    from ht_coach_app.views.match_page import MatchPage
except Exception:
    QApplication = None
    QLabel = None
    MatchPage = None


ROOT = Path(__file__).resolve().parents[1]
ADVISOR_RULE_KEYS = (
    "advisor.rule.consider_formation",
    "advisor.rule.use_formation",
    "advisor.rule.strongest_sector",
    "advisor.rule.exposed_sector",
    "advisor.rule.defensive_exposure",
    "advisor.rule.defensive_observation",
    "advisor.rule.inefficient_flank",
    "advisor.rule.best_attack_matchup",
    "advisor.rule.low_possession",
    "advisor.rule.unbalanced_attack",
    "advisor.rule.unbalanced_defense",
    "advisor.rule.favorable_concentration",
    "advisor.rule.favorable_attack_concentration",
    "advisor.rule.unfavorable_concentration",
    "advisor.rule.unfavorable_attack_concentration",
    "advisor.rule.keep_lineup_change",
    "advisor.rule.revert_lineup_change",
    "advisor.rule.neutral_lineup_change",
)
ADVISOR_LABEL_KEYS = (
    "advisor.title",
    "advisor.empty",
    "advisor.estimated_win",
    "advisor.card.action",
    "advisor.card.observation",
    "advisor.card.warning",
    "advisor.impact.high",
    "advisor.impact.medium",
    "advisor.impact.low",
    "advisor.impact.observation",
    "advisor.confidence.high",
    "advisor.confidence.medium",
    "advisor.confidence.low",
    "advisor.category.lineup",
    "advisor.category.formation",
    "advisor.category.strength",
    "advisor.category.weakness",
    "advisor.category.balance",
    "advisor.sector.left_defense",
    "advisor.sector.central_defense",
    "advisor.sector.right_defense",
    "advisor.sector.midfield",
    "advisor.sector.left_attack",
    "advisor.sector.central_attack",
    "advisor.sector.right_attack",
    "advisor.sector_article.left_defense",
    "advisor.sector_article.central_defense",
    "advisor.sector_article.right_defense",
    "advisor.sector_article.midfield",
    "advisor.sector_article.left_attack",
    "advisor.sector_article.central_attack",
    "advisor.sector_article.right_attack",
    "advisor.sector_exposed.left_defense",
    "advisor.sector_exposed.central_defense",
    "advisor.sector_exposed.right_defense",
    "advisor.sector_exposed.midfield",
    "advisor.sector_exposed.left_attack",
    "advisor.sector_exposed.central_attack",
    "advisor.sector_exposed.right_attack",
)
ADVISOR_FORMAT_PARAMS = {
    "current_formation": "3-5-2",
    "formation": "4-5-1",
    "win_delta": "+1.2 pp",
    "sector_summary": "midfield +2",
    "sector": "mediocampo",
    "sector_with_article": "El mediocampo",
    "sector_exposed": "El mediocampo queda expuesto",
    "opponent_sector": "defensa central",
    "value": "42",
    "gap": "6",
    "possession": "42.0%",
    "incoming": "Nuevo jugador",
    "outgoing": "Jugador anterior",
    "slot": "Inner Midfielder (IM)",
}


def _catalog(language):
    return json.loads(
        (ROOT / "resources" / "i18n" / f"{language}.json").read_text(
            encoding="utf-8"
        )
    )


def _lookup(catalog, key):
    value = catalog
    for part in key.split("."):
        value = value[part]
    return value


def _advisor_rule_code_keys():
    source = (
        ROOT / "engine" / "advisor" / "recommendation_engine.py"
    ).read_text(encoding="utf-8")
    return sorted(
        set(
            re.findall(
                r"advisor\.rule\.[a-z_]+\.(?:title|explanation)",
                source,
            )
        )
    )


def _ratings():
    return TeamRatingsResult(
        left_defense=42,
        central_defense=42,
        right_defense=42,
        midfield=40,
        left_attack=30,
        central_attack=31,
        right_attack=30,
    )


def _result_with_advisor(*recommendations):
    return MatchAnalysisResult(
        player_count=20,
        opponent_name="Rival FC",
        analyzed_formations=["3-5-2"],
        formations=[
            FormationAnalysisResult(
                formation_name="3-5-2",
                recommended_tactic="NORMAL",
                tactic_level=5.0,
                win_probability=0.40,
                draw_probability=0.30,
                loss_probability=0.30,
                possession=0.50,
                expected_goals=2.0,
                opponent_expected_goals=1.2,
                is_recommended=True,
                team_ratings=_ratings(),
                opponent_ratings=_ratings(),
            )
        ],
        tactical_advisor=list(recommendations),
    )


def _legacy_observation(title_key, explanation_key):
    return Recommendation(
        code="legacy",
        title_key=title_key,
        explanation_key=explanation_key,
        category=RecommendationCategory.BALANCE,
        impact_score=0.0,
        confidence=RecommendationConfidence.MEDIUM,
        card_type=RecommendationCardType.OBSERVATION,
        params={
            "sector": "{advisor.sector.midfield}",
            "gap": "6",
        },
    )


class AdvisorLocalizationCoverageTest(unittest.TestCase):
    def test_every_advisor_title_key_exists_in_english(self):
        catalog = _catalog("en")
        for key in ADVISOR_RULE_KEYS:
            self.assertIsInstance(_lookup(catalog, f"{key}.title"), str)

    def test_every_advisor_title_key_exists_in_spanish(self):
        catalog = _catalog("es")
        for key in ADVISOR_RULE_KEYS:
            self.assertIsInstance(_lookup(catalog, f"{key}.title"), str)

    def test_every_advisor_explanation_key_exists_in_english(self):
        catalog = _catalog("en")
        for key in ADVISOR_RULE_KEYS:
            self.assertIsInstance(_lookup(catalog, f"{key}.explanation"), str)

    def test_every_advisor_explanation_key_exists_in_spanish(self):
        catalog = _catalog("es")
        for key in ADVISOR_RULE_KEYS:
            self.assertIsInstance(_lookup(catalog, f"{key}.explanation"), str)

    def test_all_advisor_rule_keys_referenced_by_code_resolve(self):
        service = LocalizationService("en")
        for key in _advisor_rule_code_keys():
            text = service.t(key, **ADVISOR_FORMAT_PARAMS)
            self.assertFalse(text.startswith("advisor."))
            self.assertNotIn("{", text)

    def test_declared_advisor_label_keys_resolve_in_both_languages(self):
        for language in ("en", "es"):
            service = LocalizationService(language)
            for key in ADVISOR_LABEL_KEYS:
                text = service.t(key, value="+1.0 pp")
                self.assertFalse(text.startswith("advisor."))
                self.assertNotEqual(text, TRANSLATION_UNAVAILABLE)

    def test_spanish_exposed_sector_title_resolves(self):
        service = LocalizationService("es")
        text = service.t(
            "advisor.rule.exposed_sector.title",
            sector="mediocampo",
            sector_with_article="El mediocampo",
            sector_exposed="El mediocampo queda expuesto",
        )

        self.assertEqual(text, "El mediocampo queda expuesto")

    def test_spanish_exposed_sector_explanation_resolves(self):
        service = LocalizationService("es")
        text = service.t(
            "advisor.rule.exposed_sector.explanation",
            sector="mediocampo",
            gap="6",
        )

        self.assertIn("6 puntos", text)
        self.assertFalse(text.startswith("advisor."))

    def test_spanish_unbalanced_attack_title_resolves(self):
        service = LocalizationService("es")

        self.assertEqual(
            service.t("advisor.rule.unbalanced_attack.title"),
            "Tu ataque está concentrado en un enfrentamiento desfavorable",
        )

    def test_spanish_unbalanced_attack_explanation_resolves(self):
        service = LocalizationService("es")
        text = service.t("advisor.rule.unbalanced_attack.explanation")

        self.assertIn("contexto táctico", text)

    def test_strongest_sector_spanish_title_uses_correct_article(self):
        service = LocalizationService("es")

        self.assertEqual(
            service.t(
                "advisor.rule.strongest_sector.title",
                sector="mediocampo",
                sector_with_article="El mediocampo",
            ),
            "El mediocampo es tu zona más fuerte",
        )

    def test_missing_spanish_key_falls_back_to_english(self, tmp_path=None):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "en.json").write_text(
                json.dumps({"advisor": {"only_en": "English fallback"}}),
                encoding="utf-8",
            )
            (path / "es.json").write_text(
                json.dumps({"advisor": {}}),
                encoding="utf-8",
            )

            service = LocalizationService("es", resources_path=path)

            self.assertEqual(service.t("advisor.only_en"), "English fallback")

    def test_missing_key_in_all_languages_does_not_expose_raw_key(self):
        service = LocalizationService("es")

        text = service.t("advisor.rule.missing_forever.title")

        self.assertEqual(text, "No disponible")

    def test_parameter_substitution_works_in_english(self):
        service = LocalizationService("en")
        text = service.t(
            "advisor.rule.use_formation.title",
            formation="4-5-1",
            current_formation="3-5-2",
        )

        self.assertEqual(text, "Use 4-5-1 instead of 3-5-2")

    def test_parameter_substitution_works_in_spanish(self):
        service = LocalizationService("es")
        text = service.t(
            "advisor.rule.keep_lineup_change.title",
            incoming="Jugador nuevo",
            slot="Mediocampista central",
        )

        self.assertEqual(text, "Mantén a Jugador nuevo en Mediocampista central")

    def test_missing_parameters_do_not_crash_or_leave_braces(self):
        service = LocalizationService("es")
        text = service.t("advisor.rule.keep_lineup_change.title")

        self.assertIn("No disponible", text)
        self.assertNotIn(TRANSLATION_UNAVAILABLE, text)
        self.assertNotIn("{incoming}", text)
        self.assertNotIn("{slot}", text)


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class AdvisorLocalizationViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_advisor_cards_never_render_raw_dotted_keys(self):
        configure_localization("es")
        result = _result_with_advisor(
            _legacy_observation(
                "advisor.rule.exposed_sector.title",
                "advisor.rule.exposed_sector.explanation",
            ),
            _legacy_observation(
                "advisor.rule.unbalanced_attack.title",
                "advisor.rule.unbalanced_attack.explanation",
            ),
        )
        page = MatchPage()
        page.show_results(result)

        labels = [label.text() for label in page.findChildren(QLabel)]

        self.assertFalse(
            any(label.startswith("advisor.") for label in labels),
            labels,
        )

    def test_language_switching_refreshes_advisor_content(self):
        recommendation = _legacy_observation(
            "advisor.rule.unbalanced_attack.title",
            "advisor.rule.unbalanced_attack.explanation",
        )
        result = _result_with_advisor(recommendation)
        page = MatchPage()

        configure_localization("es")
        page.show_results(result)
        spanish_labels = [label.text() for label in page.findChildren(QLabel)]
        self.assertIn("Asesor táctico", spanish_labels)
        self.assertIn(
            "Tu ataque está concentrado en un enfrentamiento desfavorable",
            spanish_labels,
        )

        configure_localization("en")
        page.show_results(result)
        english_labels = [label.text() for label in page.findChildren(QLabel)]
        self.assertIn("Tactical Advisor", english_labels)
        self.assertIn(
            "Attack is concentrated in an unfavorable matchup",
            english_labels,
        )
