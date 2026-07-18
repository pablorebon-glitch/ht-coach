import json
from dataclasses import asdict, dataclass

from ht_coach_app.core.paths import user_data_dir


@dataclass(frozen=True)
class AppSettings:
    language: str = "en"


class AppSettingsRepository:
    def __init__(self, storage_path=None):
        self.storage_path = storage_path or (
            user_data_dir() / "app_settings.json"
        )

    def load(self):
        if not self.storage_path.exists():
            return AppSettings()

        try:
            with open(
                self.storage_path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return AppSettings()

        language = str(data.get("language", "en")).strip() or "en"
        if language not in {"en", "es"}:
            language = "en"

        return AppSettings(language=language)

    def save(self, settings):
        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            self.storage_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                asdict(settings),
                file,
                indent=2,
                ensure_ascii=False,
            )

        return settings
