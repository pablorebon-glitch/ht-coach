from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChangeValueDelta:
    label: str
    old_value: float
    new_value: float
    difference: float
    value_type: str = "number"


@dataclass(frozen=True)
class LastChange:
    incoming_player: str
    outgoing_player: str
    slot: str
    formation_name: str


@dataclass(frozen=True)
class PositionFitChange:
    previous_player_score: float
    current_player_score: float
    difference: float


@dataclass(frozen=True)
class ChangeSummary:
    code: str
    title_key: str
    description_key: str


@dataclass(frozen=True)
class ChangeAnalysisResult:
    last_change: LastChange
    position_fit: PositionFitChange
    team_impact: list[ChangeValueDelta] = field(default_factory=list)
    sector_changes: list[ChangeValueDelta] = field(default_factory=list)
    summary: ChangeSummary | None = None
    schema_version: int = 1
