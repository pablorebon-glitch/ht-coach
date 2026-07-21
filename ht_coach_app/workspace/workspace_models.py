from dataclasses import dataclass, field
from enum import Enum

from ht_coach_app.core.localization import t


class ManualLineupState(str, Enum):
    OPTIMIZED = "optimized"
    MANUALLY_MODIFIED = "manually_modified"
    RECOMMENDATIONS_AVAILABLE = "recommendations_available"
    RECOMMENDATIONS_APPLIED = "recommendations_applied"


@dataclass(frozen=True)
class WorkspaceReplacementCandidate:
    player_id: str
    player_name: str
    score: float
    score_difference: float
    reason: str = ""


@dataclass(frozen=True)
class WorkspaceBenchPlayer:
    player_id: str
    player_name: str
    best_position: str
    best_position_label: str
    best_position_abbreviation: str
    score: float
    compatibility_label: str = ""
    is_selected: bool = False
    is_incoming_preview: bool = False


@dataclass(frozen=True)
class WorkspaceReplacementPreview:
    formation_name: str
    slot_id: str
    role: str
    current_player_id: str
    current_player_name: str
    replacement_player_id: str
    replacement_player_name: str
    current_score: float
    replacement_score: float
    score_difference: float
    revision: int = 0


@dataclass(frozen=True)
class WorkspaceSwapPreview:
    formation_name: str
    source_slot_id: str
    target_slot_id: str
    source_player_id: str
    source_player_name: str
    target_player_id: str
    target_player_name: str
    source_role: str
    target_role: str
    revision: int = 0


@dataclass(frozen=True)
class WorkspaceModification:
    formation_name: str
    slot_id: str
    role: str
    original_player_name: str
    replacement_player_name: str
    score_difference: float
    kind: str = "replacement"
    source_slot_id: str = ""
    target_slot_id: str = ""
    incoming_player_id: str = ""
    outgoing_player_id: str = ""
    before_lineup_ids: tuple[str, ...] = ()
    after_lineup_ids: tuple[str, ...] = ()
    revision_before: int = 0
    revision_after: int = 0
    interaction_source: str = ""
    previous_slot_score: float | None = None
    current_slot_score: float | None = None


@dataclass(frozen=True)
class RecommendationImpact:
    affected_sectors: tuple[str, ...] = ()
    sector_deltas: tuple[tuple[str, float], ...] = ()
    aggregate_improvement: float = 0.0
    objective: str = "formation_score"


@dataclass(frozen=True)
class PositionRecommendation:
    player_id: str
    player_display_name: str
    current_slot_id: str
    recommended_slot_id: str
    current_position: str
    recommended_position: str
    current_side: str = ""
    recommended_side: str = ""
    impact: RecommendationImpact = field(default_factory=RecommendationImpact)
    explanation_code: str = "position_swap_improves_internal_contribution"
    confidence: str = "medium"
    status: str = "available"


@dataclass(frozen=True)
class OrderRecommendation:
    player_id: str
    player_display_name: str
    slot_id: str
    current_order: str
    recommended_order: str
    current_order_side: str = ""
    recommended_order_side: str = ""
    position: str = ""
    side: str = ""
    impact: RecommendationImpact = field(default_factory=RecommendationImpact)
    explanation_code: str = "order_improves_internal_contribution"
    confidence: str = "medium"
    status: str = "available"


@dataclass(frozen=True)
class LineupRecommendationSet:
    manual_state: ManualLineupState = ManualLineupState.OPTIMIZED
    position_recommendations: tuple[PositionRecommendation, ...] = ()
    order_recommendations: tuple[OrderRecommendation, ...] = ()
    objective: str = "formation_score"
    current_score: float = 0.0
    recommended_score: float = 0.0
    stale_revision: int = 0
    no_position_recommendation_reason: str = ""
    no_order_recommendation_reason: str = ""

    @property
    def has_recommendations(self):
        return bool(self.position_recommendations or self.order_recommendations)


@dataclass(frozen=True)
class WorkspaceState:
    original_boards: dict = field(default_factory=dict)
    workspace_boards: dict = field(default_factory=dict)
    current_formation_name: str = ""
    selected_player_id: str = ""
    replacement_preview: WorkspaceReplacementPreview | None = None
    swap_preview: WorkspaceSwapPreview | None = None
    history: tuple[WorkspaceModification, ...] = ()
    redo_stack: tuple[WorkspaceModification, ...] = ()
    evaluation_state: str = "original"
    revision: int = 0
    last_error: str = ""
    manual_lineup_state: ManualLineupState = ManualLineupState.OPTIMIZED
    recommendations: LineupRecommendationSet = field(
        default_factory=LineupRecommendationSet
    )

    @property
    def dirty(self):
        return bool(self.history)

    @property
    def current_board(self):
        return self.workspace_boards.get(self.current_formation_name)

    @property
    def status_label(self):
        if self.evaluation_state == "updating":
            return t("workspace.updating")
        if self.evaluation_state == "failed":
            return t("workspace.failed")
        if self.swap_preview is not None:
            return t("workspace.swap_preview")
        if self.replacement_preview is not None:
            return t("workspace.replacement_preview")
        if self.evaluation_state == "evaluated":
            return t("workspace.evaluated")
        if self.manual_lineup_state == ManualLineupState.RECOMMENDATIONS_APPLIED:
            return t("workspace.recommendations_applied")
        if self.manual_lineup_state == ManualLineupState.RECOMMENDATIONS_AVAILABLE:
            return t("workspace.recommendations_available")
        if self.dirty or self.evaluation_state == "pending":
            return t("workspace.manual_modified")
        return t("workspace.original")

    @property
    def status_state(self):
        if self.evaluation_state == "updating":
            return "updating"
        if self.evaluation_state == "failed":
            return "failed"
        if self.replacement_preview is not None or self.swap_preview is not None:
            return "preview"
        if self.evaluation_state == "evaluated":
            return "evaluated"
        if self.manual_lineup_state == ManualLineupState.RECOMMENDATIONS_APPLIED:
            return "evaluated"
        if self.manual_lineup_state == ManualLineupState.RECOMMENDATIONS_AVAILABLE:
            return "preview"
        if self.dirty or self.evaluation_state == "pending":
            return "pending"
        return "clean"

    @property
    def has_preview(self):
        return self.replacement_preview is not None or self.swap_preview is not None
