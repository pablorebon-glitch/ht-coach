from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from types import SimpleNamespace
from pathlib import Path

from engine.advisor.recommendation import Recommendation
from engine.advisor.recommendation_engine import RecommendationEngine
from engine.advisor.recommendation_types import (
    RecommendationCardType,
    RecommendationCategory,
    RecommendationConfidence,
)
from engine.analyzers.team_rater import TeamRater
from engine.squad_health.availability_service import (
    CURRENT_AVAILABLE,
    FULL_STRENGTH,
    AvailabilityService,
)
from engine.optimizers.formation_optimizer import FormationOptimizer
from engine.optimizers.tactic_optimizer import TacticOptimizer
from engine.optimizers.training_constrained_optimizer import (
    TrainingConstrainedFormationOptimizer,
)
from engine.weekly_training.player_identity import player_training_id
from engine.match_intelligence import MatchIntelligenceEngine
from engine.match_intelligence.models import (
    IntelligenceItem,
    MatchIntelligenceResult,
    MatchupInsight,
    MatchupMatrix,
    TacticalFocus,
    TeamProfile,
)
from engine.ratings import (
    SOURCE_HATTRICK_DECIMAL,
    SOURCE_HT_COACH_INTERNAL,
    SectorComparison as RatingSectorComparison,
    build_sector_comparisons,
)
from ht_coach_app.core.position_formatting import format_position
from ht_coach_app.core.position_formatting import normalize_position_key
from ht_coach_app.core.localization import t
from ht_coach_app.core.side_formatting import normalize_side_value
from ht_coach_app.change_analysis.models import ChangeAnalysisResult
from ht_coach_app.change_analysis.service import (
    change_analysis_result_from_dict,
    change_analysis_result_to_dict,
)
from ht_coach_app.reasoning.decision_lab import DecisionLab
from ht_coach_app.reasoning.explanation_formatter import (
    confidence_level_label,
    decision_lab_result_to_dict,
    format_decision_lab_copy,
    localized_decision_reason,
    localized_decision_risk,
    localized_decision_summary,
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
from ht_coach_app.widgets.formation_board.formation_layouts import (
    get_formation_layout,
)
from models.formations import (
    DEFAULT_FORMATION_NAMES,
    FORMATION_BY_NAME,
)
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.position import Position
from models.side import Side


class MatchWorkspaceValidationError(ValueError):
    pass


MATCH_TYPE_LEAGUE = "LEAGUE"
MATCH_TYPE_CUP = "CUP"
ANALYSIS_OWNER_NEW_MATCH_DRAFT = "NEW_MATCH_DRAFT"
ANALYSIS_OWNER_SAVED_MATCH = "SAVED_MATCH"


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
    indirect_defense: float | None = None
    indirect_attack: float | None = None


@dataclass(frozen=True)
class SectorRatingComparisonResult:
    matchup_key: str
    our_sector: str
    opponent_sector: str
    our_value: float | None
    opponent_value: float | None
    our_scale: str
    opponent_scale: str
    difference: float | None
    advantage: str
    comparable: bool


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
    sector_rating_comparisons: list[SectorRatingComparisonResult] = field(
        default_factory=list
    )
    objective_trace: dict = field(default_factory=dict)


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
    match_intelligence: MatchIntelligenceResult | None = None
    change_analysis: ChangeAnalysisResult | None = None
    tactical_advisor: list[Recommendation] = field(default_factory=list)
    availability_mode: str = CURRENT_AVAILABLE
    availability_warning: str = ""
    unavailable_players_count: int = 0
    match_type: str = MATCH_TYPE_LEAGUE
    training_conflict_warning: str = ""
    analysis_owner_type: str = ""
    analysis_owner_id: str = ""
    training_cycle_id: str = ""
    weekly_cycle_revision_used: str = ""
    training_context_timestamp: str = ""
    training_context_summary: str = ""
    training_context_stale: bool = False
    recommendation_id: str = ""
    recommendation_revision: int = 0
    manual_lineup_revision: int = 0
    lineup_decision: dict | None = None

    @property
    def recommended_formation(self):
        if not self.formations:
            return None

        recommendation_id = str(self.recommendation_id or "").strip()
        for formation in self.formations:
            if recommendation_id and formation.formation_name == recommendation_id:
                return formation

        for formation in self.formations:
            if formation.is_recommended:
                return formation

        return self.formations[0]


class MatchWorkspaceService:
    def __init__(
        self,
        opponent_service,
        importer=None,
        optimizer=FormationOptimizer.optimize_against,
        availability_service=None
    ):
        self._opponent_service = opponent_service
        self._importer = importer
        self._optimizer = optimizer
        self._availability_service = availability_service or AvailabilityService()

    def supported_formations(self):
        return list(FORMATION_BY_NAME.keys())

    def default_formations(self):
        return list(DEFAULT_FORMATION_NAMES)

    def list_opponents(self):
        if hasattr(self._opponent_service, "list_opponents_by_recency"):
            return self._opponent_service.list_opponents_by_recency()
        return self._opponent_service.list_opponents()

    def load_players_count(self, players_csv_path, availability_mode=CURRENT_AVAILABLE):
        return len(
            self._load_players(
                players_csv_path,
                availability_mode=availability_mode,
            )
        )

    def load_players(self, players_csv_path, availability_mode=CURRENT_AVAILABLE):
        self.validate_players_csv_path(players_csv_path)
        return self._load_players(
            players_csv_path,
            availability_mode=availability_mode,
        )

    def analyze(
        self,
        players_csv_path,
        opponent_name,
        formation_names,
        availability_mode=CURRENT_AVAILABLE,
        match_type=MATCH_TYPE_LEAGUE,
        required_player_ids=None,
        training_rules=None,
        required_slot_classes=None,
    ):
        match_type = self._normalize_match_type(match_type)
        self.validate_inputs(
            players_csv_path,
            opponent_name,
            formation_names
        )

        mode = self._availability_service.normalize_mode(
            availability_mode
        )
        all_players = self._load_all_players(
            players_csv_path
        )
        players = self._eligible_players(
            all_players,
            mode,
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

        training_conflict_warning = ""

        if match_type == MATCH_TYPE_CUP:
            if training_rules is None:
                raise MatchWorkspaceValidationError(
                    "Automatic training rules unavailable for Cup/Friendly analysis."
                )
            required_players = self._resolve_required_players(
                players,
                required_player_ids or (),
            )
            constrained_results = TrainingConstrainedFormationOptimizer.optimize_against(
                players,
                formations,
                opponent.ratings,
                required_players,
                training_rules,
                required_slot_classes=required_slot_classes or {},
            )
            engine_results = [
                item.formation_result for item in constrained_results
            ]
            unplaced_names = sorted(
                {
                    player.name
                    for item in constrained_results
                    for player in item.unplaced_required_players
                }
            )
            conflict_names = sorted(
                {
                    conflict.get("player_name", "")
                    for item in constrained_results[:1]
                    for conflict in getattr(item, "training_conflicts", ())
                    if conflict.get("player_name", "")
                }
            )
            warning_names = sorted(set(unplaced_names) | set(conflict_names))
            if warning_names:
                training_conflict_warning = t(
                    "match.training_conflict_warning",
                    players=", ".join(warning_names),
                )
        else:
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
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            availability_mode=mode,
            availability_warning=self._availability_warning(mode),
            unavailable_players_count=self._unavailable_count(all_players),
            match_type=match_type,
            training_conflict_warning=training_conflict_warning,
            training_cycle_id="",
            weekly_cycle_revision_used="",
            training_context_timestamp="",
            training_context_summary="",
            training_context_stale=False,
            recommendation_id=(
                mapped_results[0].formation_name if mapped_results else ""
            ),
            recommendation_revision=1,
            manual_lineup_revision=0,
        )

        return self._with_decision_lab(
            result
        )

    @staticmethod
    def _resolve_required_players(players, required_player_ids):
        required_ids = set(required_player_ids)
        if not required_ids:
            return []
        return [
            player for player in players
            if player_training_id(player) in required_ids
        ]

    def analyze_workspace(
        self,
        players_csv_path,
        opponent_name,
        workspace_state,
        availability_mode=CURRENT_AVAILABLE,
        match_type=MATCH_TYPE_LEAGUE,
    ):
        formation_names = list(
            workspace_state.workspace_boards.keys()
        )
        match_type = self._normalize_match_type(match_type)
        self.validate_inputs(
            players_csv_path,
            opponent_name,
            formation_names
        )

        mode = self._availability_service.normalize_mode(
            availability_mode
        )
        all_players = self._load_all_players(
            players_csv_path
        )
        players = self._eligible_players(
            all_players,
            mode,
        )
        players_by_name = {
            player.name: player
            for player in players
        }
        opponent = self._opponent_service.get_opponent(
            opponent_name
        )

        if opponent is None:
            raise MatchWorkspaceValidationError(
                "Select a saved opponent."
            )

        engine_results = []
        for board in workspace_state.workspace_boards.values():
            if board.formation_name not in FORMATION_BY_NAME:
                continue

            lineup = self._lineup_from_board(
                board,
                players_by_name,
            )
            ratings = TeamRater.calculate(
                lineup
            )
            tactic_result = TacticOptimizer.optimize(
                ratings,
                opponent.ratings,
                lineup=lineup,
            )
            engine_results.append(
                SimpleNamespace(
                    formation=FORMATION_BY_NAME[board.formation_name],
                    lineup=lineup,
                    tactic=tactic_result.tactic,
                    tactic_level=tactic_result.tactic_level,
                    ratings=tactic_result.ratings,
                    match_evaluation=tactic_result.match_evaluation,
                    probabilities=tactic_result.probabilities,
                    tested_lineups=0,
                    tested_order_configurations=0,
                    order_finalists=0,
                    tested_tactics=tactic_result.tested_tactics,
                    baseline_win_probability=tactic_result.baseline_win_probability,
                    best_normal_win_probability=tactic_result.baseline_win_probability,
                    best_order_win_probability=tactic_result.baseline_win_probability,
                )
            )

        engine_results.sort(
            key=lambda result: result.probabilities.win,
            reverse=True,
        )
        mapped_results = self._map_results(
            engine_results,
            opponent.ratings,
        )
        result = MatchAnalysisResult(
            player_count=len(players),
            opponent_name=opponent.name,
            formations=mapped_results,
            players_csv_filename=Path(players_csv_path).name,
            analyzed_formations=formation_names,
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            availability_mode=mode,
            availability_warning=self._availability_warning(mode),
            unavailable_players_count=self._unavailable_count(all_players),
            match_type=match_type,
            recommendation_id="",
            recommendation_revision=0,
            manual_lineup_revision=1,
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

    @staticmethod
    def _normalize_match_type(match_type):
        value = getattr(match_type, "value", match_type)
        if value in {MATCH_TYPE_LEAGUE, MATCH_TYPE_CUP}:
            return value
        raise MatchWorkspaceValidationError("Select a valid match type.")

    def validate_players_csv_path(self, players_csv_path):
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

    def _load_players(self, players_csv_path, availability_mode=CURRENT_AVAILABLE):
        players = self._load_all_players(players_csv_path)
        return self._eligible_players(
            players,
            self._availability_service.normalize_mode(availability_mode),
        )

    def _load_all_players(self, players_csv_path):
        importer = self._importer

        if importer is None:
            from importers.csv_importer import load_players

            importer = load_players

        return importer(
            str(players_csv_path)
        )

    def _eligible_players(self, players, mode):
        return self._availability_service.eligible_players(
            players,
            mode,
        )

    def _unavailable_count(self, players):
        return len(
            self._availability_service.unavailable_records(players)
        )

    @staticmethod
    def _availability_warning(mode):
        if mode == FULL_STRENGTH:
            return t("match.availability_full_strength_warning")

        return ""

    def _lineup_from_board(self, board, players_by_name):
        lineup = Lineup()

        for slot in board.slots:
            if slot.player is None:
                raise MatchWorkspaceValidationError(
                    "Workspace lineup must contain eleven players."
                )

            player = players_by_name.get(
                slot.player.player_name
            )
            if player is None:
                raise MatchWorkspaceValidationError(
                    f"{slot.player.player_name} is not available in the loaded roster."
                )

            lineup.players.append(
                LineupPlayer(
                    player=player,
                    position=self._position(
                        slot.player.position
                    ),
                    side=self._side(
                        slot.player.side
                    ),
                    order=self._order(
                        slot.player.individual_order
                    ),
                    order_side=(
                        self._side(slot.player.order_side)
                        if slot.player.order_side
                        else None
                    ),
                )
            )

        if len(lineup.players) != 11:
            raise MatchWorkspaceValidationError(
                "Workspace lineup must contain eleven players."
            )

        return lineup

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
            team_ratings = self._map_team_ratings(
                getattr(result, "ratings", None)
            )
            mapped_opponent_ratings = self._map_team_ratings(
                opponent_ratings
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
                    team_ratings=team_ratings,
                    opponent_ratings=mapped_opponent_ratings,
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
                    ),
                    sector_rating_comparisons=self._map_sector_comparisons(
                        team_ratings,
                        mapped_opponent_ratings,
                    ),
                    objective_trace=self._objective_trace_to_dict(
                        getattr(result, "objective_trace", None)
                    ),
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
    def _objective_trace_to_dict(trace):
        if trace is None:
            return {}
        if hasattr(trace, "to_dict"):
            return trace.to_dict()
        if isinstance(trace, dict):
            return dict(trace)
        return {}

    def apply_official_pre_override(self, result, official_pre_ratings):
        """HF-02.2 source-selection policy, applied as a pure
        post-processing step over an already-computed `MatchAnalysisResult`
        -- never touches the optimizer, the rating formulas, or how the
        other candidate formations were computed. Only the *recommended*
        formation's "our" ratings are substituted (Official PRE was
        captured for whatever lineup was actually submitted, not for
        every candidate formation the optimizer explored), and only its
        `sector_rating_comparisons` and the top-level `match_intelligence`
        result are recomputed from that substitution.

        Returns `result` unchanged if there's no recommended formation or
        no usable Official PRE ratings.
        """
        from engine.ratings.rating_source_policy import select_our_ratings

        recommended = result.recommended_formation
        if recommended is None:
            return result

        selection = select_our_ratings(
            recommended.team_ratings, official_pre_ratings
        )
        if not selection.is_official:
            return result

        official_team_ratings = self._map_team_ratings(selection.ratings)
        sector_rating_comparisons = [
            _sector_rating_comparison_from_domain(comparison)
            for comparison in build_sector_comparisons(
                official_team_ratings,
                recommended.opponent_ratings,
                our_scale=selection.scale,
            )
        ]

        updated_formations = [
            (
                self._with_official_ratings(
                    formation, official_team_ratings, sector_rating_comparisons
                )
                if formation is recommended
                else formation
            )
            for formation in result.formations
        ]
        updated_result = replace(result, formations=updated_formations)

        try:
            match_intelligence = MatchIntelligenceEngine().analyze(updated_result)
        except Exception:
            match_intelligence = result.match_intelligence

        return replace(updated_result, match_intelligence=match_intelligence)

    @staticmethod
    def _with_official_ratings(formation, official_team_ratings, sector_rating_comparisons):
        return replace(
            formation,
            team_ratings=official_team_ratings,
            sector_rating_comparisons=sector_rating_comparisons,
        )

    def _with_decision_lab(self, result):
        try:
            decision_lab = DecisionLab().analyze(result)
        except Exception:
            decision_lab = None
        try:
            match_intelligence = MatchIntelligenceEngine().analyze(result)
        except Exception:
            match_intelligence = None

        enriched = MatchAnalysisResult(
            player_count=result.player_count,
            opponent_name=result.opponent_name,
            formations=result.formations,
            players_csv_filename=result.players_csv_filename,
            analyzed_formations=result.analyzed_formations,
            completed_at=result.completed_at,
            decision_lab=decision_lab,
            match_intelligence=match_intelligence,
            change_analysis=result.change_analysis,
            tactical_advisor=result.tactical_advisor,
            availability_mode=result.availability_mode,
            availability_warning=result.availability_warning,
            unavailable_players_count=result.unavailable_players_count,
            match_type=result.match_type,
            training_conflict_warning=result.training_conflict_warning,
            analysis_owner_type=result.analysis_owner_type,
            analysis_owner_id=result.analysis_owner_id,
            training_cycle_id=result.training_cycle_id,
            weekly_cycle_revision_used=result.weekly_cycle_revision_used,
            training_context_timestamp=result.training_context_timestamp,
            training_context_summary=result.training_context_summary,
            training_context_stale=result.training_context_stale,
            recommendation_id=result.recommendation_id,
            recommendation_revision=result.recommendation_revision,
            manual_lineup_revision=result.manual_lineup_revision,
            lineup_decision=result.lineup_decision,
        )
        return with_tactical_advisor(enriched)

    def refresh_presentational_analysis(self, result):
        return self._with_decision_lab(result)

    @staticmethod
    def _map_team_ratings(ratings):
        if ratings is None:
            return TeamRatingsResult()

        def _required(sector):
            # HF-02.2: a sector attribute may exist but hold None (e.g. a
            # partial Official PRE capture) -- "or 0.0" catches that,
            # unlike a getattr default (which only applies when the
            # attribute is missing entirely). Never fail on optional data.
            return float(getattr(ratings, sector, 0.0) or 0.0)

        return TeamRatingsResult(
            left_defense=_required("left_defense"),
            central_defense=_required("central_defense"),
            right_defense=_required("right_defense"),
            midfield=_required("midfield"),
            left_attack=_required("left_attack"),
            central_attack=_required("central_attack"),
            right_attack=_required("right_attack"),
            indirect_defense=_optional_float(
                getattr(ratings, "indirect_defense", None)
            ),
            indirect_attack=_optional_float(
                getattr(ratings, "indirect_attack", None)
            ),
        )

    @staticmethod
    def _map_sector_comparisons(team_ratings, opponent_ratings):
        return [
            _sector_rating_comparison_from_domain(comparison)
            for comparison in build_sector_comparisons(
                team_ratings,
                opponent_ratings,
                our_scale=SOURCE_HATTRICK_DECIMAL,
                opponent_scale=SOURCE_HATTRICK_DECIMAL,
            )
        ]

    @staticmethod
    def _enum_value(value):
        return getattr(
            value,
            "value",
            value
        )

    @staticmethod
    def _position(value):
        normalized = normalize_position_key(value)
        try:
            return Position(normalized)
        except ValueError as exc:
            raise MatchWorkspaceValidationError(
                "Workspace lineup contains an unsupported position."
            ) from exc

    @staticmethod
    def _side(value):
        normalized = normalize_side_value(value)
        try:
            return Side(normalized)
        except ValueError:
            return Side.CENTER

    @staticmethod
    def _order(value):
        raw = getattr(value, "value", value)
        for order in Order:
            if raw in {order.value, order.name}:
                return order
        return Order.NORMAL


def match_analysis_result_to_dict(result):
    data = asdict(result)
    data["decision_lab"] = decision_lab_result_to_dict(
        result.decision_lab
    )
    data["match_intelligence"] = match_intelligence_result_to_dict(
        result.match_intelligence
    )
    data["change_analysis"] = change_analysis_result_to_dict(
        result.change_analysis
    )
    data["tactical_advisor"] = [
        _recommendation_to_dict(recommendation)
        for recommendation in result.tactical_advisor
    ]
    return data


def match_analysis_result_from_dict(data):
    result = MatchAnalysisResult(
        player_count=int(data.get("player_count", 0)),
        opponent_name=data.get("opponent_name", ""),
        players_csv_filename=data.get("players_csv_filename", ""),
        analyzed_formations=list(data.get("analyzed_formations", [])),
        completed_at=data.get("completed_at", ""),
        availability_mode=data.get("availability_mode", CURRENT_AVAILABLE),
        availability_warning=data.get("availability_warning", ""),
        unavailable_players_count=int(data.get("unavailable_players_count", 0)),
        match_type=data.get("match_type", MATCH_TYPE_LEAGUE),
        training_conflict_warning=data.get("training_conflict_warning", ""),
        training_cycle_id=data.get("training_cycle_id", ""),
        weekly_cycle_revision_used=data.get("weekly_cycle_revision_used", ""),
        training_context_timestamp=data.get("training_context_timestamp", ""),
        training_context_summary=data.get("training_context_summary", ""),
        training_context_stale=bool(data.get("training_context_stale", False)),
        recommendation_id=(
            data.get("recommendation_id", "")
            or _recommended_formation_name_from_items(data.get("formations", []))
        ),
        recommendation_revision=int(data.get("recommendation_revision", 0)),
        manual_lineup_revision=int(data.get("manual_lineup_revision", 0)),
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
                sector_rating_comparisons=[
                    _sector_rating_comparison_from_dict(comparison)
                    for comparison in item.get("sector_rating_comparisons", [])
                    if isinstance(comparison, dict)
                ],
                objective_trace=dict(item.get("objective_trace", {})),
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
        ),
        match_intelligence=match_intelligence_result_from_dict(
            data.get("match_intelligence")
        ),
        change_analysis=change_analysis_result_from_dict(
            data.get("change_analysis")
        ),
        tactical_advisor=[
            recommendation
            for recommendation in (
                _recommendation_from_dict(item)
                for item in data.get("tactical_advisor", [])
                if isinstance(item, dict)
            )
            if recommendation is not None
        ],
        analysis_owner_type=data.get("analysis_owner_type", ""),
        analysis_owner_id=data.get("analysis_owner_id", ""),
        lineup_decision=data.get("lineup_decision"),
    )

    decision_lab = result.decision_lab
    match_intelligence = result.match_intelligence

    if decision_lab is None and result.formations:
        try:
            decision_lab = DecisionLab().analyze(result)
        except Exception:
            decision_lab = None

    if match_intelligence is None and result.formations:
        try:
            match_intelligence = MatchIntelligenceEngine().analyze(result)
        except Exception:
            match_intelligence = None

    if (
        decision_lab is not result.decision_lab
        or match_intelligence is not result.match_intelligence
    ):
        return MatchAnalysisResult(
            player_count=result.player_count,
            opponent_name=result.opponent_name,
            formations=result.formations,
            players_csv_filename=result.players_csv_filename,
            analyzed_formations=result.analyzed_formations,
            completed_at=result.completed_at,
            decision_lab=decision_lab,
            match_intelligence=match_intelligence,
            change_analysis=result.change_analysis,
            tactical_advisor=result.tactical_advisor,
            availability_mode=result.availability_mode,
            availability_warning=result.availability_warning,
            unavailable_players_count=result.unavailable_players_count,
            match_type=result.match_type,
            training_conflict_warning=result.training_conflict_warning,
            analysis_owner_type=result.analysis_owner_type,
            analysis_owner_id=result.analysis_owner_id,
            training_cycle_id=result.training_cycle_id,
            weekly_cycle_revision_used=result.weekly_cycle_revision_used,
            training_context_timestamp=result.training_context_timestamp,
            training_context_summary=result.training_context_summary,
            training_context_stale=result.training_context_stale,
            recommendation_id=result.recommendation_id,
            recommendation_revision=result.recommendation_revision,
            manual_lineup_revision=result.manual_lineup_revision,
            lineup_decision=result.lineup_decision,
        )

    return result


def with_tactical_advisor(result):
    try:
        recommendations = RecommendationEngine().recommend(result)
    except Exception:
        recommendations = []

    return MatchAnalysisResult(
        player_count=result.player_count,
        opponent_name=result.opponent_name,
        formations=result.formations,
        players_csv_filename=result.players_csv_filename,
        analyzed_formations=result.analyzed_formations,
        completed_at=result.completed_at,
        decision_lab=result.decision_lab,
        match_intelligence=getattr(result, "match_intelligence", None),
        change_analysis=result.change_analysis,
        tactical_advisor=list(recommendations),
        availability_mode=result.availability_mode,
        availability_warning=result.availability_warning,
        unavailable_players_count=result.unavailable_players_count,
        match_type=result.match_type,
        training_conflict_warning=result.training_conflict_warning,
        analysis_owner_type=result.analysis_owner_type,
        analysis_owner_id=result.analysis_owner_id,
        training_cycle_id=result.training_cycle_id,
        weekly_cycle_revision_used=result.weekly_cycle_revision_used,
        training_context_timestamp=result.training_context_timestamp,
        training_context_summary=result.training_context_summary,
        training_context_stale=result.training_context_stale,
        recommendation_id=result.recommendation_id,
        recommendation_revision=result.recommendation_revision,
        manual_lineup_revision=result.manual_lineup_revision,
        lineup_decision=result.lineup_decision,
    )


def _recommended_formation_name_from_items(items):
    for item in items or []:
        if not isinstance(item, dict):
            continue
        if item.get("is_recommended", False):
            return item.get("formation_name", "")
    return ""


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
        indirect_defense=_optional_float(data.get("indirect_defense")),
        indirect_attack=_optional_float(data.get("indirect_attack")),
    )


def _optional_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sector_rating_comparison_from_domain(comparison):
    if isinstance(comparison, RatingSectorComparison):
        return SectorRatingComparisonResult(
            matchup_key=comparison.matchup_key,
            our_sector=comparison.our_sector,
            opponent_sector=comparison.opponent_sector,
            our_value=comparison.our_value,
            opponent_value=comparison.opponent_value,
            our_scale=comparison.our_scale,
            opponent_scale=comparison.opponent_scale,
            difference=comparison.difference,
            advantage=comparison.advantage,
            comparable=comparison.comparable,
        )
    return comparison


def _sector_rating_comparison_from_dict(data):
    return SectorRatingComparisonResult(
        matchup_key=data.get("matchup_key", ""),
        our_sector=data.get("our_sector", ""),
        opponent_sector=data.get("opponent_sector", ""),
        our_value=_optional_float(data.get("our_value")),
        opponent_value=_optional_float(data.get("opponent_value")),
        our_scale=data.get("our_scale", ""),
        opponent_scale=data.get("opponent_scale", ""),
        difference=_optional_float(data.get("difference")),
        advantage=data.get("advantage", "not_directly_comparable"),
        comparable=bool(data.get("comparable", False)),
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
            lineup_decision=data.get("lineup_decision"),
            schema_version=int(data.get("schema_version", 1))
        )
    except (TypeError, ValueError, AttributeError):
        return None


def match_intelligence_result_to_dict(result):
    if result is None:
        return None
    return asdict(result)


def match_intelligence_result_from_dict(data):
    if not isinstance(data, dict):
        return None

    try:
        return MatchIntelligenceResult(
            formation_name=data.get("formation_name", ""),
            our_profile=_team_profile_from_dict(
                data.get("our_profile", {})
            ),
            opponent_profile=_team_profile_from_dict(
                data.get("opponent_profile", {})
            ),
            our_attack_matchups=tuple(
                _matchup_insight_from_dict(item)
                for item in data.get("our_attack_matchups", [])
                if isinstance(item, dict)
            ),
            opponent_attack_matchups=tuple(
                _matchup_insight_from_dict(item)
                for item in data.get("opponent_attack_matchups", [])
                if isinstance(item, dict)
            ),
            opportunities=tuple(
                _intelligence_item_from_dict(item)
                for item in data.get("opportunities", [])
                if isinstance(item, dict)
            ),
            risks=tuple(
                _intelligence_item_from_dict(item)
                for item in data.get("risks", [])
                if isinstance(item, dict)
            ),
            tactical_focuses=tuple(
                _tactical_focus_from_dict(item)
                for item in data.get("tactical_focuses", [])
                if isinstance(item, dict)
            ),
            summary_key=data.get("summary_key", ""),
            summary_params=dict(data.get("summary_params", {})),
            matrix=_matchup_matrix_from_dict(data.get("matrix", {})),
            schema_version=int(data.get("schema_version", 1)),
        )
    except (TypeError, ValueError, AttributeError):
        return None


def _team_profile_from_dict(data):
    return TeamProfile(
        strongest_sector=data.get("strongest_sector", ""),
        weakest_sector=data.get("weakest_sector", ""),
        most_balanced_area=data.get("most_balanced_area", ""),
        most_vulnerable_area=data.get("most_vulnerable_area", ""),
    )


def _matchup_insight_from_dict(data):
    return MatchupInsight(
        code=data.get("code", ""),
        perspective=data.get("perspective", ""),
        attack_sector=data.get("attack_sector", ""),
        defense_sector=data.get("defense_sector", ""),
        attack_value=float(data.get("attack_value", 0.0)),
        defense_value=float(data.get("defense_value", 0.0)),
        difference=float(data.get("difference", 0.0)),
        classification=data.get("classification", ""),
        advantage=data.get("advantage", ""),
        interpretation_key=data.get("interpretation_key", ""),
        params=dict(data.get("params", {})),
        is_best_route=bool(data.get("is_best_route", False)),
        is_worst_route=bool(data.get("is_worst_route", False)),
    )


def _intelligence_item_from_dict(data):
    return IntelligenceItem(
        code=data.get("code", ""),
        title_key=data.get("title_key", ""),
        description_key=data.get("description_key", ""),
        confidence=data.get("confidence", ""),
        severity=data.get("severity", ""),
        params=dict(data.get("params", {})),
        values=dict(data.get("values", {})),
    )


def _tactical_focus_from_dict(data):
    return TacticalFocus(
        code=data.get("code", ""),
        title_key=data.get("title_key", ""),
        description_key=data.get("description_key", ""),
        params=dict(data.get("params", {})),
    )


def _matchup_matrix_from_dict(data):
    if not isinstance(data, dict):
        return MatchupMatrix()
    return MatchupMatrix(
        our_attack_rows=tuple(
            _matchup_insight_from_dict(item)
            for item in data.get("our_attack_rows", [])
            if isinstance(item, dict)
        ),
        opponent_attack_rows=tuple(
            _matchup_insight_from_dict(item)
            for item in data.get("opponent_attack_rows", [])
            if isinstance(item, dict)
        ),
    )


def _recommendation_to_dict(recommendation):
    return {
        "code": recommendation.code,
        "title_key": recommendation.title_key,
        "explanation_key": recommendation.explanation_key,
        "category": recommendation.category.value,
        "card_type": recommendation.card_type.value,
        "impact_score": recommendation.impact_score,
        "confidence": recommendation.confidence.value,
        "estimated_win_delta": recommendation.estimated_win_delta,
        "params": dict(recommendation.params),
        "sector_deltas": list(recommendation.sector_deltas),
    }


def _recommendation_from_dict(data):
    try:
        return Recommendation(
            code=data.get("code", ""),
            title_key=data.get("title_key", ""),
            explanation_key=data.get("explanation_key", ""),
            category=RecommendationCategory(
                data.get("category", RecommendationCategory.BALANCE.value)
            ),
            card_type=RecommendationCardType(
                data.get("card_type", RecommendationCardType.OBSERVATION.value)
            ),
            impact_score=float(data.get("impact_score", 0.0)),
            confidence=RecommendationConfidence(
                data.get("confidence", RecommendationConfidence.LOW.value)
            ),
            estimated_win_delta=float(data.get("estimated_win_delta", 0.0)),
            params=dict(data.get("params", {})),
            sector_deltas=tuple(data.get("sector_deltas", ())),
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
                (
                    f"{t('decision_lab.recommendation_confidence')}: "
                    f"{confidence_level_label(result.decision_lab.confidence.level)}"
                ),
                (
                    f"{t('change.summary')}: "
                    f"{localized_decision_summary(result.decision_lab.summary)}"
                ),
            ]
        )

        for reason in result.decision_lab.reasons[:3]:
            title, description = localized_decision_reason(reason)
            lines.append(f"- {title}: {description}")

        for risk in result.decision_lab.risks[:2]:
            title, description = localized_decision_risk(risk)
            lines.append(
                f"- {t('decision_lab.copy.risks')}: {title}: {description}"
            )

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
            key=lambda slot: (slot.normalized_y, slot.normalized_x),
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
