from __future__ import annotations

from dataclasses import dataclass, field

from engine.squad_intelligence.enums import ClubStrategy


@dataclass(frozen=True)
class ClubAdvisorContext:
    """Everything the Club Advisor reads. Deliberately holds only
    *already-computed* outputs from other modules (Squad Intelligence
    reports, training coverage rows, squad-relative context) -- it
    never recomputes a player's role, training fit or rating itself."""

    strategy: ClubStrategy = ClubStrategy.SUSTAINABLE_GROWTH
    squad_reports: tuple = ()
    squad_context: object = None
    active_training_type: str = ""
    coverage_rows: tuple = ()
    training_priority_rows: tuple = ()
    has_historical_data: bool = False
    evolution_result: object = None
    insights_result: object = None
    players_by_position: dict = field(default_factory=dict)

    @property
    def roster_size(self) -> int:
        return len(self.squad_reports)

    @property
    def has_active_training(self) -> bool:
        return bool(self.active_training_type)
