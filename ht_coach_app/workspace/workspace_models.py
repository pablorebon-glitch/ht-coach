from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkspaceReplacementCandidate:
    player_id: str
    player_name: str
    score: float
    score_difference: float
    reason: str = ""


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


@dataclass(frozen=True)
class WorkspaceModification:
    formation_name: str
    slot_id: str
    role: str
    original_player_name: str
    replacement_player_name: str
    score_difference: float


@dataclass(frozen=True)
class WorkspaceState:
    original_boards: dict = field(default_factory=dict)
    workspace_boards: dict = field(default_factory=dict)
    current_formation_name: str = ""
    selected_player_id: str = ""
    replacement_preview: WorkspaceReplacementPreview | None = None
    history: tuple[WorkspaceModification, ...] = ()
    redo_stack: tuple[WorkspaceModification, ...] = ()
    evaluation_state: str = "original"

    @property
    def dirty(self):
        return bool(self.history)

    @property
    def current_board(self):
        return self.workspace_boards.get(self.current_formation_name)

    @property
    def status_label(self):
        if self.replacement_preview is not None:
            return "Replacement Preview"
        if self.evaluation_state == "evaluated":
            return "Evaluated Workspace"
        if self.dirty or self.evaluation_state == "pending":
            return "Modified Workspace - Pending Recalculation"
        return "Original Recommendation"

    @property
    def status_state(self):
        if self.replacement_preview is not None:
            return "preview"
        if self.evaluation_state == "evaluated":
            return "evaluated"
        if self.dirty or self.evaluation_state == "pending":
            return "pending"
        return "clean"
