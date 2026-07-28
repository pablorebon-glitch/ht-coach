from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.history.enums import _StableEnum
from engine.history.evolution.comparison_models import SectorEvolution, Trend


class LineupChangeStatus(_StableEnum):
    ADDED = "added"
    REMOVED = "removed"
    KEPT = "kept"


@dataclass(frozen=True)
class LineupPlayerChange:
    """A single player's change between two snapshots. Only ever built
    by matching on player_id (preferred) or player_name (fallback) —
    never by lineup row position, so reordered lineups compare
    correctly. Change flags for KEPT players are always False for
    ADDED/REMOVED entries, since there's nothing to compare against."""

    player_id: str
    player_name: str
    status: LineupChangeStatus
    previous_position: str = ""
    current_position: str = ""
    position_changed: bool = False
    previous_order: str = ""
    current_order: str = ""
    order_changed: bool = False
    previous_order_side: str = ""
    current_order_side: str = ""
    order_side_changed: bool = False
    previous_number: int | None = None
    current_number: int | None = None
    number_changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "status": self.status.value,
            "previous_position": self.previous_position,
            "current_position": self.current_position,
            "position_changed": self.position_changed,
            "previous_order": self.previous_order,
            "current_order": self.current_order,
            "order_changed": self.order_changed,
            "previous_order_side": self.previous_order_side,
            "current_order_side": self.current_order_side,
            "order_side_changed": self.order_side_changed,
            "previous_number": self.previous_number,
            "current_number": self.current_number,
            "number_changed": self.number_changed,
        }


@dataclass(frozen=True)
class LineupEvolution:
    changes: tuple[LineupPlayerChange, ...] = ()

    @property
    def players_added(self) -> tuple[LineupPlayerChange, ...]:
        return tuple(c for c in self.changes if c.status == LineupChangeStatus.ADDED)

    @property
    def players_removed(self) -> tuple[LineupPlayerChange, ...]:
        return tuple(c for c in self.changes if c.status == LineupChangeStatus.REMOVED)

    @property
    def players_kept(self) -> tuple[LineupPlayerChange, ...]:
        return tuple(c for c in self.changes if c.status == LineupChangeStatus.KEPT)

    @property
    def position_changes(self) -> tuple[LineupPlayerChange, ...]:
        return tuple(c for c in self.players_kept if c.position_changed)

    @property
    def order_changes(self) -> tuple[LineupPlayerChange, ...]:
        return tuple(c for c in self.players_kept if c.order_changed)

    @property
    def order_side_changes(self) -> tuple[LineupPlayerChange, ...]:
        return tuple(c for c in self.players_kept if c.order_side_changed)

    @property
    def number_changes(self) -> tuple[LineupPlayerChange, ...]:
        return tuple(c for c in self.players_kept if c.number_changed)

    def to_dict(self) -> dict[str, Any]:
        return {"changes": [change.to_dict() for change in self.changes]}


@dataclass(frozen=True)
class FormationEvolution:
    previous_formation: str = ""
    current_formation: str = ""
    changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_formation": self.previous_formation,
            "current_formation": self.current_formation,
            "changed": self.changed,
        }


@dataclass(frozen=True)
class TacticalEvolution:
    previous_tactic: str = ""
    current_tactic: str = ""
    tactic_changed: bool = False
    previous_tactic_level: float | None = None
    current_tactic_level: float | None = None
    tactic_level_delta: float | None = None
    previous_attitude: str = ""
    current_attitude: str = ""
    attitude_changed: bool = False
    previous_confidence: str = ""
    current_confidence: str = ""
    confidence_changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_tactic": self.previous_tactic,
            "current_tactic": self.current_tactic,
            "tactic_changed": self.tactic_changed,
            "previous_tactic_level": self.previous_tactic_level,
            "current_tactic_level": self.current_tactic_level,
            "tactic_level_delta": self.tactic_level_delta,
            "previous_attitude": self.previous_attitude,
            "current_attitude": self.current_attitude,
            "attitude_changed": self.attitude_changed,
            "previous_confidence": self.previous_confidence,
            "current_confidence": self.current_confidence,
            "confidence_changed": self.confidence_changed,
        }


@dataclass(frozen=True)
class MetricDelta:
    previous: float | None = None
    current: float | None = None
    delta: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous": self.previous,
            "current": self.current,
            "delta": self.delta,
        }


@dataclass(frozen=True)
class PredictionEvolution:
    expected_goals: MetricDelta = field(default_factory=MetricDelta)
    opponent_expected_goals: MetricDelta = field(default_factory=MetricDelta)
    win_probability: MetricDelta = field(default_factory=MetricDelta)
    draw_probability: MetricDelta = field(default_factory=MetricDelta)
    loss_probability: MetricDelta = field(default_factory=MetricDelta)
    possession: MetricDelta = field(default_factory=MetricDelta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_goals": self.expected_goals.to_dict(),
            "opponent_expected_goals": self.opponent_expected_goals.to_dict(),
            "win_probability": self.win_probability.to_dict(),
            "draw_probability": self.draw_probability.to_dict(),
            "loss_probability": self.loss_probability.to_dict(),
            "possession": self.possession.to_dict(),
        }


@dataclass(frozen=True)
class OverallEvolution:
    overall_rating_delta: float | None = None
    average_sector_delta: float | None = None
    best_improved_sector: str | None = None
    worst_sector: str | None = None
    improved_sector_count: int = 0
    declined_sector_count: int = 0
    unchanged_sector_count: int = 0
    overall_trend: Trend = Trend.UNCHANGED

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_rating_delta": self.overall_rating_delta,
            "average_sector_delta": self.average_sector_delta,
            "best_improved_sector": self.best_improved_sector,
            "worst_sector": self.worst_sector,
            "improved_sector_count": self.improved_sector_count,
            "declined_sector_count": self.declined_sector_count,
            "unchanged_sector_count": self.unchanged_sector_count,
            "overall_trend": self.overall_trend.value,
        }


@dataclass(frozen=True)
class HistoricalEvolutionResult:
    current_snapshot_id: str
    previous_snapshot_id: str
    overall: OverallEvolution
    sectors: tuple[SectorEvolution, ...]
    formation: FormationEvolution
    tactical: TacticalEvolution
    lineup: LineupEvolution
    prediction: PredictionEvolution
    evolution_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_snapshot_id": self.current_snapshot_id,
            "previous_snapshot_id": self.previous_snapshot_id,
            "overall": self.overall.to_dict(),
            "sectors": [sector.to_dict() for sector in self.sectors],
            "formation": self.formation.to_dict(),
            "tactical": self.tactical.to_dict(),
            "lineup": self.lineup.to_dict(),
            "prediction": self.prediction.to_dict(),
            "evolution_score": self.evolution_score,
        }
