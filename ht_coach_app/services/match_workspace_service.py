from dataclasses import dataclass, field
from pathlib import Path

from engine.optimizers.formation_optimizer import FormationOptimizer
from models.formations import FORMATIONS


SUPPORTED_FORMATIONS = {
    formation.name: formation
    for formation in FORMATIONS
    if formation.name in {"3-5-2", "4-5-1"}
}


class MatchWorkspaceValidationError(ValueError):
    pass


@dataclass(frozen=True)
class LineupPlayerResult:
    position: str
    side: str
    order: str
    order_side: str
    player_name: str


@dataclass(frozen=True)
class FormationAnalysisResult:
    formation_name: str
    recommended_tactic: str
    tactic_level: float
    win_probability: float
    draw_probability: float
    loss_probability: float
    possession: float
    expected_goals: float
    opponent_expected_goals: float
    lineup: list[LineupPlayerResult] = field(
        default_factory=list
    )
    is_recommended: bool = False


@dataclass(frozen=True)
class MatchAnalysisResult:
    player_count: int
    opponent_name: str
    formations: list[FormationAnalysisResult]


class MatchWorkspaceService:
    def __init__(
        self,
        opponent_service,
        importer=None,
        optimizer=FormationOptimizer.optimize_against
    ):
        self._opponent_service = opponent_service
        self._importer = importer
        self._optimizer = optimizer

    def supported_formations(self):
        return list(SUPPORTED_FORMATIONS.keys())

    def list_opponents(self):
        return self._opponent_service.list_opponents()

    def load_players_count(self, players_csv_path):
        return len(
            self._load_players(players_csv_path)
        )

    def analyze(self, players_csv_path, opponent_name, formation_names):
        self.validate_inputs(
            players_csv_path,
            opponent_name,
            formation_names
        )

        players = self._load_players(
            players_csv_path
        )

        opponent = self._opponent_service.get_opponent(
            opponent_name
        )

        if opponent is None:
            raise MatchWorkspaceValidationError(
                "Select a saved opponent."
            )

        formations = [
            SUPPORTED_FORMATIONS[name]
            for name in formation_names
        ]

        engine_results = self._optimizer(
            players,
            formations,
            opponent.ratings
        )

        mapped_results = self._map_results(
            engine_results
        )

        return MatchAnalysisResult(
            player_count=len(players),
            opponent_name=opponent.name,
            formations=mapped_results
        )

    def validate_inputs(
        self,
        players_csv_path,
        opponent_name,
        formation_names
    ):
        normalized_path = str(players_csv_path).strip()
        path = Path(normalized_path)

        if not normalized_path:
            raise MatchWorkspaceValidationError(
                "Select a players.csv file."
            )

        if not path.exists():
            raise MatchWorkspaceValidationError(
                "The selected players.csv file does not exist."
            )

        if not opponent_name:
            raise MatchWorkspaceValidationError(
                "Select a saved opponent."
            )

        if not formation_names:
            raise MatchWorkspaceValidationError(
                "Select at least one formation."
            )

        unsupported = [
            name for name in formation_names
            if name not in SUPPORTED_FORMATIONS
        ]

        if unsupported:
            raise MatchWorkspaceValidationError(
                "Unsupported formation selected."
            )

    def _load_players(self, players_csv_path):
        importer = self._importer

        if importer is None:
            from importers.csv_importer import load_players

            importer = load_players

        return importer(
            str(players_csv_path)
        )

    def _map_results(self, engine_results):
        mapped = []

        for index, result in enumerate(engine_results):
            mapped.append(
                FormationAnalysisResult(
                    formation_name=result.formation.name,
                    recommended_tactic=self._enum_value(
                        result.tactic
                    ),
                    tactic_level=float(
                        result.tactic_level
                    ),
                    win_probability=float(
                        result.probabilities.win
                    ),
                    draw_probability=float(
                        result.probabilities.draw
                    ),
                    loss_probability=float(
                        result.probabilities.loss
                    ),
                    possession=float(
                        result.match_evaluation.possession
                    ),
                    expected_goals=float(
                        result.match_evaluation.expected_goals
                    ),
                    opponent_expected_goals=float(
                        result.match_evaluation.opponent_expected_goals
                    ),
                    lineup=[
                        self._map_lineup_player(lineup_player)
                        for lineup_player in result.lineup.players
                    ],
                    is_recommended=(index == 0)
                )
            )

        return mapped

    def _map_lineup_player(self, lineup_player):
        return LineupPlayerResult(
            position=self._enum_value(
                lineup_player.position
            ),
            side=self._enum_value(
                lineup_player.side
            ),
            order=self._enum_value(
                lineup_player.order
            ),
            order_side=(
                self._enum_value(lineup_player.order_side)
                if lineup_player.order_side is not None
                else ""
            ),
            player_name=lineup_player.player.name
        )

    @staticmethod
    def _enum_value(value):
        return getattr(
            value,
            "value",
            value
        )
