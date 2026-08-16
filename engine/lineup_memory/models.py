"""Match plan revision models (Alpha 0.6.6, Part 2).

Pure, Qt-independent data shapes representing "what changed between the
previously planned lineup and a new recommendation" -- never touches the
optimizer, never recomputes a rating. Everything here is built from
already-computed `FormationAnalysisResult`/`LineupPlayerResult` objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChangedSlot:
    number: int
    position: str
    side: str
    previous_player_name: str
    new_player_name: str
    previous_order: str
    new_order: str
    previous_order_side: str
    new_order_side: str

    @property
    def player_changed(self) -> bool:
        return self.previous_player_name != self.new_player_name

    @property
    def order_changed(self) -> bool:
        return (
            self.previous_order != self.new_order
            or self.previous_order_side != self.new_order_side
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "position": self.position,
            "side": self.side,
            "previous_player_name": self.previous_player_name,
            "new_player_name": self.new_player_name,
            "previous_order": self.previous_order,
            "new_order": self.new_order,
            "previous_order_side": self.previous_order_side,
            "new_order_side": self.new_order_side,
        }


@dataclass(frozen=True)
class SectorDelta:
    sector: str
    previous_value: float
    new_value: float
    delta: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector": self.sector,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "delta": self.delta,
        }


@dataclass(frozen=True)
class MatchPlanRevision:
    """Everything Part 2 asks for: a typed comparison between a
    previously saved/planned lineup and a new recommendation. Never
    fabricated -- every field is either directly read from the two
    `FormationAnalysisResult`s being compared, or empty/zero when there
    was no previous plan to compare against."""

    match_record_id: str = ""
    previous_lineup: tuple = ()
    new_lineup: tuple = ()
    changed_slots: tuple[ChangedSlot, ...] = ()
    changed_players: tuple[str, ...] = ()
    changed_orders: tuple[ChangedSlot, ...] = ()
    changed_formation: bool = False
    previous_formation: str = ""
    new_formation: str = ""
    changed_tactic: bool = False
    previous_tactic: str = ""
    new_tactic: str = ""
    changed_team_attitude: bool = False
    previous_team_attitude: str = ""
    new_team_attitude: str = ""
    sector_deltas: tuple[SectorDelta, ...] = ()
    possession_delta: float = 0.0
    xg_delta: float = 0.0
    win_probability_delta: float = 0.0
    created_at: str = ""
    source_csv: str = ""
    evidence: tuple = ()
    significance: str = ""

    @property
    def has_previous_plan(self) -> bool:
        return bool(self.previous_lineup)

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_slots) or self.changed_formation or self.changed_tactic

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_record_id": self.match_record_id,
            "changed_slots": [item.to_dict() for item in self.changed_slots],
            "changed_players": list(self.changed_players),
            "changed_orders": [item.to_dict() for item in self.changed_orders],
            "changed_formation": self.changed_formation,
            "previous_formation": self.previous_formation,
            "new_formation": self.new_formation,
            "changed_tactic": self.changed_tactic,
            "previous_tactic": self.previous_tactic,
            "new_tactic": self.new_tactic,
            "changed_team_attitude": self.changed_team_attitude,
            "previous_team_attitude": self.previous_team_attitude,
            "new_team_attitude": self.new_team_attitude,
            "sector_deltas": [item.to_dict() for item in self.sector_deltas],
            "possession_delta": self.possession_delta,
            "xg_delta": self.xg_delta,
            "win_probability_delta": self.win_probability_delta,
            "created_at": self.created_at,
            "source_csv": self.source_csv,
            "significance": self.significance,
        }
