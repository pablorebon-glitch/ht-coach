import json
from dataclasses import asdict, dataclass, field

from ht_coach_app.core.paths import user_data_dir
from ht_coach_app.services.match_workspace_service import (
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
)
from models.formations import DEFAULT_FORMATION_NAMES


@dataclass
class MatchWorkspaceSettings:
    players_csv_path: str = ""
    opponent_name: str = ""
    selected_formations: list[str] = field(
        default_factory=lambda: list(DEFAULT_FORMATION_NAMES)
    )


class MatchWorkspaceRepository:
    def __init__(self, storage_path=None, result_storage_path=None):
        self.storage_path = storage_path or (
            user_data_dir() / "match_workspace.json"
        )
        self.result_storage_path = result_storage_path or (
            user_data_dir() / "match_last_result.json"
        )

    def load(self):
        if not self.storage_path.exists():
            return MatchWorkspaceSettings()

        with open(
            self.storage_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return MatchWorkspaceSettings(
            players_csv_path=data.get("players_csv_path", ""),
            opponent_name=data.get("opponent_name", ""),
            selected_formations=list(
                data.get(
                    "selected_formations",
                    DEFAULT_FORMATION_NAMES
                )
            ),
        )

    def save(self, settings):
        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            self.storage_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                asdict(settings),
                file,
                indent=2
            )

        return settings

    def load_last_result(self):
        if not self.result_storage_path.exists():
            return None

        with open(
            self.result_storage_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return match_analysis_result_from_dict(data)

    def save_last_result(self, result):
        self.result_storage_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            self.result_storage_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                match_analysis_result_to_dict(result),
                file,
                indent=2
            )

        return result
