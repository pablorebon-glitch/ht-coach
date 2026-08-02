import json
from dataclasses import asdict, dataclass, field, replace

from ht_coach_app.core.paths import user_data_dir
from ht_coach_app.services.match_workspace_service import (
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
)
from models.formations import DEFAULT_FORMATION_NAMES


@dataclass
class MatchWorkspaceSettings:
    players_csv_path: str = ""
    recent_players_csv_paths: list[str] = field(default_factory=list)
    opponent_name: str = ""
    selected_formations: list[str] = field(
        default_factory=lambda: list(DEFAULT_FORMATION_NAMES)
    )
    squad_availability_mode: str = "current_available"
    squad_training_focus: str = "unknown"
    squad_planning_horizon: str = "current"
    transfer_planning_objective: str = "balanced"
    transfer_budget_tier: str = "unspecified"
    transfer_age_strategy: str = "balanced"
    transfer_training_preference: str = "any"
    transfer_specialty_preference: str = "no_preference"
    squad_selected_tab: str = "ideal"
    match_section_states: dict[str, bool] = field(default_factory=dict)


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
            recent_players_csv_paths=list(
                data.get("recent_players_csv_paths", [])
            ),
            opponent_name=data.get("opponent_name", ""),
            selected_formations=list(
                data.get(
                    "selected_formations",
                    DEFAULT_FORMATION_NAMES
                )
            ),
            squad_availability_mode=data.get(
                "squad_availability_mode",
                "current_available"
            ),
            squad_training_focus=data.get(
                "squad_training_focus",
                "unknown",
            ),
            squad_planning_horizon=data.get(
                "squad_planning_horizon",
                "current",
            ),
            transfer_planning_objective=data.get(
                "transfer_planning_objective",
                "balanced",
            ),
            transfer_budget_tier=data.get(
                "transfer_budget_tier",
                "unspecified",
            ),
            transfer_age_strategy=data.get(
                "transfer_age_strategy",
                "balanced",
            ),
            transfer_training_preference=data.get(
                "transfer_training_preference",
                "any",
            ),
            transfer_specialty_preference=data.get(
                "transfer_specialty_preference",
                "no_preference",
            ),
            squad_selected_tab=data.get(
                "squad_selected_tab",
                "ideal",
            ),
            match_section_states={
                str(key): bool(value)
                for key, value in dict(
                    data.get("match_section_states", {})
                ).items()
            },
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

    MAX_RECENT_PLAYERS_CSV = 3

    def remember_players_csv_path(self, path):
        """Records a newly loaded players.csv as the active one and adds
        it to the shared "recent" list (Squad and Match both read/write
        this same file, so loading a CSV once in either page makes it
        available in both)."""
        path = str(path or "").strip()
        settings = self.load()
        if not path:
            return settings

        recent = [path] + [
            item for item in settings.recent_players_csv_paths
            if item != path
        ]
        recent = recent[: self.MAX_RECENT_PLAYERS_CSV]

        updated = replace(
            settings,
            players_csv_path=path,
            recent_players_csv_paths=recent,
        )
        return self.save(updated)

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

    def clear_last_result(self):
        """Alpha 0.6.7 HF-02, Part 1: the cached "last analyzed
        result" can carry official PRE data already merged into its
        sector comparisons (`apply_official_pre_override`). If the
        canonical record that PRE came from gets deleted, this stale
        cache must not resurrect it on the next app load -- there is
        no reliable way to "un-merge" already-baked-in official data,
        so the safest fix is dropping the cache entirely rather than
        risking showing outdated evidence."""
        if self.result_storage_path.exists():
            self.result_storage_path.unlink()
