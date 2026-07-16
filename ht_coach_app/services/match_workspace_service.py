from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from engine.optimizers.formation_optimizer import FormationOptimizer
from ht_coach_app.core.position_formatting import format_position
from ht_coach_app.reasoning.decision_lab import DecisionLab
from ht_coach_app.reasoning.explanation_formatter import (
    decision_lab_result_to_dict,
    format_decision_lab_copy,
)
from ht_coach_app.reasoning.models import (
    ConfidenceAssessment,
    DecisionLabResult,
    DecisionReason,
    DecisionRisk,
    FormationComparison,
    RecommendedDecision,
    SectorComparison,
    TacticalObservation,
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
class TeamRatingsResult:
    left_defense: float = 0.0
    central_defense: float = 0.0
    right_defense: float = 0.0
    midfield: float = 0.0
    left_attack: float = 0.0
    central_attack: float = 0.0
    right_attack: float = 0.0


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
    team_ratings: TeamRatingsResult = field(
        default_factory=TeamRatingsResult
    )
    opponent_ratings: TeamRatingsResult = field(
        default_factory=TeamRatingsResult
    )
    baseline_win_probability: float = 0.0
    best_normal_win_probability: float = 0.0
    best_order_win_probability: float = 0.0
    final_optimized_win_probability: float = 0.0
    lineup_gain: float = 0.0
    order_gain: float = 0.0
    tactic_gain: float = 0.0
    total_gain: float = 0.0


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
    decision_lab: DecisionLabResult | None = None

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
            engine_results,
            opponent.ratings
        )

        result = MatchAnalysisResult(
            player_count=len(players),
            opponent_name=opponent.name,
            formations=mapped_results,
            players_csv_filename=Path(players_csv_path).name,
            analyzed_formations=list(formation_names),
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        return self._with_decision_lab(
            result
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

    def _map_results(self, engine_results, opponent_ratings):
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
                    is_recommended=(index == 0),
                    team_ratings=self._map_team_ratings(
                        getattr(result, "ratings", None)
                    ),
                    opponent_ratings=self._map_team_ratings(
                        opponent_ratings
                    ),
                    baseline_win_probability=float(
                        getattr(
                            result,
                            "baseline_win_probability",
                            win_probability
                        )
                    ),
                    best_normal_win_probability=float(
                        getattr(
                            result,
                            "best_normal_win_probability",
                            win_probability
                        )
                    ),
                    best_order_win_probability=float(
                        getattr(
                            result,
                            "best_order_win_probability",
                            win_probability
                        )
                    ),
                    final_optimized_win_probability=win_probability,
                    lineup_gain=(
                        float(
                            getattr(
                                result,
                                "best_normal_win_probability",
                                win_probability
                            )
                        )
                        - float(
                            getattr(
                                result,
                                "baseline_win_probability",
                                win_probability
                            )
                        )
                    ),
                    order_gain=(
                        float(
                            getattr(
                                result,
                                "best_order_win_probability",
                                win_probability
                            )
                        )
                        - float(
                            getattr(
                                result,
                                "best_normal_win_probability",
                                win_probability
                            )
                        )
                    ),
                    tactic_gain=(
                        win_probability
                        - float(
                            getattr(
                                result,
                                "best_order_win_probability",
                                win_probability
                            )
                        )
                    ),
                    total_gain=(
                        win_probability
                        - float(
                            getattr(
                                result,
                                "baseline_win_probability",
                                win_probability
                            )
                        )
                    )
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

    def _with_decision_lab(self, result):
        try:
            decision_lab = DecisionLab().analyze(result)
        except Exception:
            decision_lab = None

        return MatchAnalysisResult(
            player_count=result.player_count,
            opponent_name=result.opponent_name,
            formations=result.formations,
            players_csv_filename=result.players_csv_filename,
            analyzed_formations=result.analyzed_formations,
            completed_at=result.completed_at,
            decision_lab=decision_lab
        )

    @staticmethod
    def _map_team_ratings(ratings):
        if ratings is None:
            return TeamRatingsResult()

        return TeamRatingsResult(
            left_defense=float(
                getattr(ratings, "left_defense", 0.0)
            ),
            central_defense=float(
                getattr(ratings, "central_defense", 0.0)
            ),
            right_defense=float(
                getattr(ratings, "right_defense", 0.0)
            ),
            midfield=float(
                getattr(ratings, "midfield", 0.0)
            ),
            left_attack=float(
                getattr(ratings, "left_attack", 0.0)
            ),
            central_attack=float(
                getattr(ratings, "central_attack", 0.0)
            ),
            right_attack=float(
                getattr(ratings, "right_attack", 0.0)
            ),
        )

    @staticmethod
    def _enum_value(value):
        return getattr(
            value,
            "value",
            value
        )


def match_analysis_result_to_dict(result):
    data = asdict(result)
    data["decision_lab"] = decision_lab_result_to_dict(
        result.decision_lab
    )
    return data


def match_analysis_result_from_dict(data):
    result = MatchAnalysisResult(
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
                team_ratings=_team_ratings_from_dict(
                    item.get("team_ratings", {})
                ),
                opponent_ratings=_team_ratings_from_dict(
                    item.get("opponent_ratings", {})
                ),
                baseline_win_probability=float(
                    item.get("baseline_win_probability", 0.0)
                ),
                best_normal_win_probability=float(
                    item.get("best_normal_win_probability", 0.0)
                ),
                best_order_win_probability=float(
                    item.get("best_order_win_probability", 0.0)
                ),
                final_optimized_win_probability=float(
                    item.get(
                        "final_optimized_win_probability",
                        item.get("win_probability", 0.0)
                    )
                ),
                lineup_gain=float(item.get("lineup_gain", 0.0)),
                order_gain=float(item.get("order_gain", 0.0)),
                tactic_gain=float(item.get("tactic_gain", 0.0)),
                total_gain=float(item.get("total_gain", 0.0)),
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
        ],
        decision_lab=_decision_lab_from_dict(
            data.get("decision_lab")
        )
    )

    if result.decision_lab is None and result.formations:
        try:
            decision_lab = DecisionLab().analyze(result)
        except Exception:
            decision_lab = None

        if decision_lab is not None:
            return MatchAnalysisResult(
                player_count=result.player_count,
                opponent_name=result.opponent_name,
                formations=result.formations,
                players_csv_filename=result.players_csv_filename,
                analyzed_formations=result.analyzed_formations,
                completed_at=result.completed_at,
                decision_lab=decision_lab
            )

    return result


def _team_ratings_from_dict(data):
    if not isinstance(data, dict):
        return TeamRatingsResult()

    return TeamRatingsResult(
        left_defense=float(data.get("left_defense", 0.0)),
        central_defense=float(data.get("central_defense", 0.0)),
        right_defense=float(data.get("right_defense", 0.0)),
        midfield=float(data.get("midfield", 0.0)),
        left_attack=float(data.get("left_attack", 0.0)),
        central_attack=float(data.get("central_attack", 0.0)),
        right_attack=float(data.get("right_attack", 0.0)),
    )


def _sector_from_dict(data):
    return SectorComparison(
        sector=data.get("sector", ""),
        our_value=float(data.get("our_value", 0.0)),
        opponent_value=float(data.get("opponent_value", 0.0)),
        relative_difference=float(data.get("relative_difference", 0.0)),
        classification=data.get("classification", "Balanced")
    )


def _decision_lab_from_dict(data):
    if not isinstance(data, dict):
        return None

    try:
        confidence = data.get("confidence", {})
        recommended = data.get("recommended_formation", {})

        return DecisionLabResult(
            recommended_formation=RecommendedDecision(
                formation=recommended.get("formation", ""),
                tactic=recommended.get("tactic", ""),
                win_probability=float(
                    recommended.get("win_probability", 0.0)
                ),
                confidence=recommended.get("confidence", "")
            ),
            headline=data.get("headline", ""),
            summary=data.get("summary", ""),
            confidence=ConfidenceAssessment(
                level=confidence.get("level", "LOW"),
                score=float(confidence.get("score", 0.0)),
                explanation=confidence.get("explanation", "")
            ),
            confidence_score=float(data.get("confidence_score", 0.0)),
            reasons=[
                DecisionReason(
                    code=item.get("code", ""),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    importance=item.get("importance", ""),
                    metric_name=item.get("metric_name", ""),
                    metric_value=float(item.get("metric_value", 0.0)),
                    comparison_value=float(
                        item.get("comparison_value", 0.0)
                    )
                )
                for item in data.get("reasons", [])
                if isinstance(item, dict)
            ],
            risks=[
                DecisionRisk(
                    code=item.get("code", ""),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    severity=item.get("severity", ""),
                    metric_name=item.get("metric_name", ""),
                    metric_value=float(item.get("metric_value", 0.0))
                )
                for item in data.get("risks", [])
                if isinstance(item, dict)
            ],
            tactical_observations=[
                TacticalObservation(
                    code=item.get("code", ""),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    metric_name=item.get("metric_name", ""),
                    metric_value=float(item.get("metric_value", 0.0))
                )
                for item in data.get("tactical_observations", [])
                if isinstance(item, dict)
            ],
            comparisons=[
                FormationComparison(
                    base_formation=item.get("base_formation", ""),
                    alternative_formation=item.get(
                        "alternative_formation",
                        ""
                    ),
                    win_probability_delta=float(
                        item.get("win_probability_delta", 0.0)
                    ),
                    draw_probability_delta=float(
                        item.get("draw_probability_delta", 0.0)
                    ),
                    loss_probability_delta=float(
                        item.get("loss_probability_delta", 0.0)
                    ),
                    possession_delta=float(
                        item.get("possession_delta", 0.0)
                    ),
                    expected_goals_delta=float(
                        item.get("expected_goals_delta", 0.0)
                    ),
                    opponent_expected_goals_delta=float(
                        item.get("opponent_expected_goals_delta", 0.0)
                    ),
                    tactic_difference=item.get("tactic_difference", ""),
                    sector_differences=[
                        _sector_from_dict(sector)
                        for sector in item.get("sector_differences", [])
                        if isinstance(sector, dict)
                    ],
                    conclusion=item.get("conclusion", "")
                )
                for item in data.get("comparisons", [])
                if isinstance(item, dict)
            ],
            opponent_weaknesses=[
                _sector_from_dict(item)
                for item in data.get("opponent_weaknesses", [])
                if isinstance(item, dict)
            ],
            our_advantages=[
                _sector_from_dict(item)
                for item in data.get("our_advantages", [])
                if isinstance(item, dict)
            ],
            our_vulnerabilities=[
                _sector_from_dict(item)
                for item in data.get("our_vulnerabilities", [])
                if isinstance(item, dict)
            ],
            lineup_gain=float(data.get("lineup_gain", 0.0)),
            order_gain=float(data.get("order_gain", 0.0)),
            tactic_gain=float(data.get("tactic_gain", 0.0)),
            total_gain=float(data.get("total_gain", 0.0)),
            schema_version=int(data.get("schema_version", 1))
        )
    except (TypeError, ValueError, AttributeError):
        return None


def format_match_summary(result):
    recommended = result.recommended_formation

    if recommended is None:
        return "No match analysis result available."

    lines = [
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

    if result.decision_lab is not None:
        lines.extend(
            [
                "",
                "Decision Lab",
                f"Confidence: {result.decision_lab.confidence.level}",
                f"Summary: {result.decision_lab.summary}",
            ]
        )

        for reason in result.decision_lab.reasons[:3]:
            lines.append(f"- {reason.title}: {reason.description}")

        for risk in result.decision_lab.risks[:2]:
            lines.append(f"- Risk: {risk.title}: {risk.description}")

    return "\n".join(lines)


def format_decision_lab(result):
    return format_decision_lab_copy(
        result.decision_lab if result is not None else None
    )


def format_recommended_lineup(result):
    recommended = result.recommended_formation

    if recommended is None:
        return "No recommended lineup available."

    lines = [
        f"Recommended XI - {recommended.formation_name}",
        "No. | Side | Position | Player | Order | Order side",
    ]

    for player in recommended.lineup:
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
