from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from engine.optimizers.formation_optimizer import FormationOptimizer
from ht_coach_app.core.position_formatting import format_position
from ht_coach_app.core.position_formatting import normalize_position_key
from ht_coach_app.core.side_formatting import normalize_side_value
from ht_coach_app.widgets.formation_board.formation_layouts import (
    get_formation_layout,
)
from models.formations import (
    DEFAULT_FORMATION_NAMES,
    FORMATION_BY_NAME,
)


class MatchWorkspaceValidationError(ValueError):
    pass


@dataclass(frozen=True)
class LineupPlayerResult:
    number: int
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
    win_probability_delta: float = 0.0
    expected_goals_delta: float = 0.0
    lineup: list[LineupPlayerResult] = field(
        default_factory=list
    )
    is_recommended: bool = False


@dataclass(frozen=True)
class MatchAnalysisResult:
    player_count: int
    opponent_name: str
    formations: list[FormationAnalysisResult]
    players_csv_filename: str = ""
    analyzed_formations: list[str] = field(
        default_factory=list
    )
    completed_at: str = ""

    @property
    def recommended_formation(self):
        if not self.formations:
            return None

        for formation in self.formations:
            if formation.is_recommended:
                return formation

        return self.formations[0]


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
        return list(FORMATION_BY_NAME.keys())

    def default_formations(self):
        return list(DEFAULT_FORMATION_NAMES)

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
            FORMATION_BY_NAME[name]
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
            formations=mapped_results,
            players_csv_filename=Path(players_csv_path).name,
            analyzed_formations=list(formation_names),
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            if name not in FORMATION_BY_NAME
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

        if engine_results:
            recommended_probabilities = engine_results[0].probabilities
            recommended_evaluation = engine_results[0].match_evaluation
            recommended_win = float(recommended_probabilities.win)
            recommended_xg = float(recommended_evaluation.expected_goals)
        else:
            recommended_win = 0.0
            recommended_xg = 0.0

        for index, result in enumerate(engine_results):
            win_probability = float(
                result.probabilities.win
            )
            expected_goals = float(
                result.match_evaluation.expected_goals
            )

            mapped.append(
                FormationAnalysisResult(
                    formation_name=result.formation.name,
                    recommended_tactic=self._enum_value(
                        result.tactic
                    ),
                    tactic_level=float(
                        result.tactic_level
                    ),
                    win_probability=win_probability,
                    draw_probability=float(
                        result.probabilities.draw
                    ),
                    loss_probability=float(
                        result.probabilities.loss
                    ),
                    possession=float(
                        result.match_evaluation.possession
                    ),
                    expected_goals=expected_goals,
                    opponent_expected_goals=float(
                        result.match_evaluation.opponent_expected_goals
                    ),
                    win_probability_delta=(
                        win_probability - recommended_win
                    ),
                    expected_goals_delta=(
                        expected_goals - recommended_xg
                    ),
                    lineup=[
                        self._map_lineup_player(
                            index + 1,
                            lineup_player
                        )
                        for index, lineup_player
                        in enumerate(result.lineup.players)
                    ],
                    is_recommended=(index == 0)
                )
            )

        return mapped

    def _map_lineup_player(self, number, lineup_player):
        return LineupPlayerResult(
            number=number,
            position=format_position(
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


def match_analysis_result_to_dict(result):
    return asdict(result)


def match_analysis_result_from_dict(data):
    return MatchAnalysisResult(
        player_count=int(data.get("player_count", 0)),
        opponent_name=data.get("opponent_name", ""),
        players_csv_filename=data.get("players_csv_filename", ""),
        analyzed_formations=list(data.get("analyzed_formations", [])),
        completed_at=data.get("completed_at", ""),
        formations=[
            FormationAnalysisResult(
                formation_name=item.get("formation_name", ""),
                recommended_tactic=item.get("recommended_tactic", ""),
                tactic_level=float(item.get("tactic_level", 0.0)),
                win_probability=float(item.get("win_probability", 0.0)),
                draw_probability=float(item.get("draw_probability", 0.0)),
                loss_probability=float(item.get("loss_probability", 0.0)),
                possession=float(item.get("possession", 0.0)),
                expected_goals=float(item.get("expected_goals", 0.0)),
                opponent_expected_goals=float(
                    item.get("opponent_expected_goals", 0.0)
                ),
                win_probability_delta=float(
                    item.get("win_probability_delta", 0.0)
                ),
                expected_goals_delta=float(
                    item.get("expected_goals_delta", 0.0)
                ),
                is_recommended=bool(item.get("is_recommended", False)),
                lineup=[
                    LineupPlayerResult(
                        number=int(player.get("number", index + 1)),
                        position=format_position(
                            player.get("position", "")
                        ),
                        side=player.get("side", ""),
                        order=player.get("order", ""),
                        order_side=player.get("order_side", ""),
                        player_name=player.get("player_name", "")
                    )
                    for index, player in enumerate(
                        item.get("lineup", [])
                    )
                ],
            )
            for item in data.get("formations", [])
        ]
    )


def format_match_summary(result):
    recommended = result.recommended_formation

    if recommended is None:
        return "No match analysis result available."

    return "\n".join(
        [
            "HT Coach Match Summary",
            f"Opponent: {result.opponent_name}",
            f"Players CSV: {result.players_csv_filename}",
            f"Players loaded: {result.player_count}",
            f"Formations analyzed: {', '.join(result.analyzed_formations)}",
            f"Completed: {result.completed_at}",
            "",
            f"Recommended formation: {recommended.formation_name}",
            f"Recommended tactic: {recommended.recommended_tactic}",
            f"Tactic level: {recommended.tactic_level:.2f}",
            f"Win: {recommended.win_probability * 100:.1f}%",
            f"Draw: {recommended.draw_probability * 100:.1f}%",
            f"Loss: {recommended.loss_probability * 100:.1f}%",
            f"Possession: {recommended.possession * 100:.1f}%",
            f"xG: {recommended.expected_goals:.2f}",
            f"Opponent xG: {recommended.opponent_expected_goals:.2f}",
        ]
    )


def format_recommended_lineup(result):
    recommended = result.recommended_formation

    if recommended is None:
        return "No recommended lineup available."

    lines = [
        f"Recommended XI - {recommended.formation_name}",
        "No. | Side | Position | Player | Order | Order side",
    ]

    for player in _lineup_in_pitch_order(recommended):
        lines.append(
            " | ".join(
                [
                    str(player.number),
                    player.side,
                    player.position,
                    player.player_name,
                    player.order,
                    player.order_side or "-",
                ]
            )
        )

    return "\n".join(lines)


def _lineup_in_pitch_order(formation):
    try:
        layouts = sorted(
            get_formation_layout(formation.formation_name),
            key=lambda slot: (-slot.normalized_y, slot.normalized_x),
        )
    except Exception:
        return formation.lineup

    remaining = list(formation.lineup)
    ordered = []

    for slot in layouts:
        match = _pop_lineup_match(
            remaining,
            slot.position,
            slot.side,
        )

        if match is not None:
            ordered.append(match)

    ordered.extend(remaining)
    return ordered


def _pop_lineup_match(players, position, side):
    for player in players:
        if (
            normalize_position_key(player.position) == position
            and normalize_side_value(player.side) == side
        ):
            players.remove(player)
            return player

    for player in players:
        if normalize_position_key(player.position) == position:
            players.remove(player)
            return player

    return None
