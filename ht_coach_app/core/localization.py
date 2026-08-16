import json
import logging

from ht_coach_app.core.paths import resources_dir


LOGGER = logging.getLogger(__name__)
TRANSLATION_UNAVAILABLE = "Not available"


class _SafeFormatParams(dict):
    def __init__(self, fallback, params):
        super().__init__(params)
        self._fallback = fallback

    def __missing__(self, key):
        LOGGER.warning("Missing localization parameter: %s", key)
        return self._fallback


class LocalizationService:
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "es": "Español",
    }

    def __init__(self, language="en", resources_path=None):
        self.resources_path = resources_path or (resources_dir() / "i18n")
        self._catalogs = {}
        self._language = "en"
        self.set_language(language)

    @property
    def language(self):
        return self._language

    def set_language(self, language):
        normalized = str(language or "en").strip()
        if normalized not in self.SUPPORTED_LANGUAGES:
            normalized = "en"
        self._language = normalized
        self._load_catalog("en")
        self._load_catalog(normalized)

    def t(self, key, **params):
        fallback = self._fallback_text()
        text = self._lookup(self._language, key)
        if text is None:
            text = self._lookup("en", key)
        if text is None:
            LOGGER.warning("Missing localization key: %s", key)
            return fallback

        try:
            return text.format_map(_SafeFormatParams(fallback, params))
        except (KeyError, ValueError):
            LOGGER.warning("Invalid localization template: %s", key)
            return fallback

    def _fallback_text(self):
        if self._language == "es":
            return "No disponible"
        return TRANSLATION_UNAVAILABLE

    def _lookup(self, language, key):
        catalog = self._load_catalog(language)
        value = catalog
        for part in str(key).split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value if isinstance(value, str) else None

    def _load_catalog(self, language):
        if language in self._catalogs:
            return self._catalogs[language]

        path = self.resources_path / f"{language}.json"
        try:
            with open(path, "r", encoding="utf-8") as file:
                catalog = json.load(file)
        except (OSError, json.JSONDecodeError):
            catalog = {}

        self._catalogs[language] = catalog
        return catalog


_service = LocalizationService()


def configure_localization(language="en", resources_path=None):
    global _service
    _service = LocalizationService(
        language=language,
        resources_path=resources_path,
    )
    return _service


def localization_service():
    return _service


def t(key, **params):
    return _service.t(key, **params)
