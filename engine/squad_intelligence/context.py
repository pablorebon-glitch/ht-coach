from __future__ import annotations

from dataclasses import dataclass, field

from engine.squad_intelligence.enums import ClubStrategy


@dataclass(frozen=True)
class PositionEvidence:
    """Squad-relative positional standing. Built from the app's existing
    player-ranking infrastructure (PlayerAnalyzer / SquadService) --
    never a second, parallel Match rating engine. `rank_in_best_position`
    is 1-based among `candidates_in_best_position` current roster
    players evaluated for that same position. `formation_slots` is the
    maximum number of that position used by any canonical Hattrick
    formation (e.g. 3 for CENTRAL_DEFENDER) -- when known, current
    performance uses it so "rank 2 of 5" for a position that regularly
    fields 3 starters is read as a genuine rotation starter, not
    conflated with "rank 2 of 2" for a position (like GOALKEEPER) that
    only ever fields one."""

    best_position: str = ""
    best_position_score: float | None = None
    rank_in_best_position: int | None = None
    candidates_in_best_position: int = 0
    alternative_positions: tuple[str, ...] = ()
    formation_slots: int = 0

    @property
    def is_available(self) -> bool:
        return bool(self.best_position) and self.rank_in_best_position is not None


@dataclass(frozen=True)
class TrainingEvidence:
    """Everything Squad Intelligence reads from the Training module --
    always through the canonical catalog/provider, never duplicated."""

    active_training_type: str = ""
    trained_skills: tuple[str, ...] = ()
    effect_for_best_position: str = ""
    priority: str = ""
    current_trained_skill_level: int | None = None
    confirmed_weekly_coverage: float | None = None
    planned_weekly_coverage: float | None = None

    @property
    def has_active_training(self) -> bool:
        return bool(self.active_training_type)


@dataclass(frozen=True)
class PlayerIntelligenceContext:
    player_id: str
    player_name: str
    player: object
    strategy: ClubStrategy = ClubStrategy.SUSTAINABLE_GROWTH
    position: PositionEvidence = field(default_factory=PositionEvidence)
    training: TrainingEvidence = field(default_factory=TrainingEvidence)
    is_available: bool = True
    availability_label: str = ""
    salary_percentile_in_squad: float | None = None
    has_stable_player_id: bool = True
    is_in_current_roster: bool = True


@dataclass(frozen=True)
class SquadIntelligenceContext:
    """Squad-relative facts shared across every player's report in a
    batch analysis -- built once, not recomputed per player.

    `positional_depth` always reflects the *structural* club (the
    complete roster -- a player out injured for four weeks still
    counts as a real, owned player). `temporary_positional_depth`
    reflects only players available *this week*; the difference
    between the two is what lets Club Advisor say "structural depth:
    adequate, temporary availability: reduced" instead of conflating a
    short-term absence with a genuine structural gap (Alpha 0.6.3)."""

    roster_size: int = 0
    positional_depth: dict = field(default_factory=dict)
    temporary_positional_depth: dict = field(default_factory=dict)
    active_training_type: str = ""
    salary_values: tuple[int, ...] = ()
    age_values: tuple[int, ...] = ()
    ages_by_position: dict = field(default_factory=dict)

    def depth_at(self, position: str) -> int:
        return self.positional_depth.get(position, 0)

    def temporary_depth_at(self, position: str) -> int:
        return self.temporary_positional_depth.get(
            position, self.positional_depth.get(position, 0)
        )
