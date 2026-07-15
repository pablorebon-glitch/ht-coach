import json
from dataclasses import asdict, dataclass, field

from ht_coach_app.core.paths import user_data_dir


@dataclass
class MatchWorkspaceSettings:
    players_csv_path: str = ""
    opponent_name: str = ""
    selected_formations: list[str] = field(
        default_factory=lambda: ["3-5-2"]
    )


class MatchWorkspaceRepository:
    def __init__(self, storage_path=None):
        self.storage_path = storage_path or (
            user_data_dir() / "match_workspace.json"
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
                data.get("selected_formations", ["3-5-2"])
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
