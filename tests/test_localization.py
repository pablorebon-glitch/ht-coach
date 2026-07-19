import json
import tempfile
import unittest
from pathlib import Path

from ht_coach_app.core.localization import (
    TRANSLATION_UNAVAILABLE,
    LocalizationService,
)
from ht_coach_app.persistence.app_settings_repository import (
    AppSettings,
    AppSettingsRepository,
)


class LocalizationServiceTest(unittest.TestCase):
    def test_language_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = AppSettingsRepository(
                Path(temp_dir) / "app_settings.json"
            )

            repository.save(AppSettings(language="es"))

            self.assertEqual(repository.load().language, "es")

    def test_advisor_verbosity_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = AppSettingsRepository(
                Path(temp_dir) / "app_settings.json"
            )

            repository.save(
                AppSettings(language="en", advisor_verbosity="simple")
            )

            self.assertEqual(repository.load().advisor_verbosity, "simple")

    def test_fallback_to_english_for_missing_translation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            resources = Path(temp_dir)
            (resources / "en.json").write_text(
                json.dumps({"hello": {"name": "Hello {name}"}}),
                encoding="utf-8",
            )
            (resources / "es.json").write_text(
                json.dumps({"hello": {}}),
                encoding="utf-8",
            )
            service = LocalizationService(
                language="es",
                resources_path=resources,
            )

            self.assertEqual(service.t("hello.name", name="Pablo"), "Hello Pablo")

    def test_missing_translation_returns_safe_fallback_without_crashing(self):
        service = LocalizationService(language="en")

        self.assertEqual(service.t("missing.translation"), TRANSLATION_UNAVAILABLE)

    def test_parameter_substitution_is_safe(self):
        service = LocalizationService(language="en")

        self.assertEqual(
            service.t("bench.players", count=3),
            "3 players",
        )

    def test_changing_language_updates_active_catalog(self):
        service = LocalizationService(language="en")

        service.set_language("es")

        self.assertEqual(service.t("settings.title"), "Configuración")
