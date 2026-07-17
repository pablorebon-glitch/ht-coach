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

    @property
    def dirty(self):
        return bool(self.history)

    @property
    def current_board(self):
        return self.workspace_boards.get(self.current_formation_name)

    @property
    def status_label(self):
        if self.replacement_preview is not None:
            return "Unsaved Changes"
        if self.dirty:
            return "Modified Workspace - Ready to Recalculate"
        return "Original Recommendation"

    @property
    def status_state(self):
        if self.replacement_preview is not None:
            return "pending"
        if self.dirty:
            return "dirty"
        return "clean"
