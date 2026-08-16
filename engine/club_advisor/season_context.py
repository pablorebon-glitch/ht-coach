from __future__ import annotations

from dataclasses import dataclass

from engine.club_advisor.enums import (
    ClubConfidence,
    CurrentCompetitiveness,
    PromotionObjective,
    SeasonPhase,
    SigningCostCategory,
)
from engine.squad_intelligence.enums import ClubStrategy

# Per the brief: "For the current reference strategy, default safely to
# WELCOME_IF_NATURAL unless explicitly configured otherwise." This is a
# season-level planning input, not configurable Club DNA -- there is still
# only one implemented ClubStrategy (SUSTAINABLE_GROWTH).
DEFAULT_PROMOTION_OBJECTIVE = PromotionObjective.WELCOME_IF_NATURAL


@dataclass(frozen=True)
class SeasonContext:
    """Everything the season-aware layer knows about the club's current
    competitive situation. Every field is optional and may be
    `None`/unknown -- this sprint does not require automated Hattrick
    league integration, and never fabricates a missing value. Missing
    context lowers confidence (see confidence.py) rather than being
    silently assumed."""

    season_number: int | None = None
    current_round: int | None = None
    total_rounds: int | None = None
    season_phase: SeasonPhase = SeasonPhase.UNKNOWN
    league_position: int | None = None
    league_team_count: int | None = None
    bot_opponent_count: int | None = None
    estimated_league_strength: str = ""
    current_competitiveness: CurrentCompetitiveness = CurrentCompetitiveness.UNKNOWN
    direct_rival_strength: str = ""
    recent_results_summary: str = ""
    promotion_objective: PromotionObjective = DEFAULT_PROMOTION_OBJECTIVE
    promotion_urgency: str = ""
    recent_major_signing: bool = False
    recent_signing_position: str = ""
    recent_signing_cost_category: SigningCostCategory = SigningCostCategory.UNKNOWN
    current_strategy: ClubStrategy = ClubStrategy.SUSTAINABLE_GROWTH
    notes: str = ""
    provenance: str = "user_provided"
    confidence: ClubConfidence = ClubConfidence.MEDIUM

    @property
    def has_any_context(self) -> bool:
        return (
            self.season_phase != SeasonPhase.UNKNOWN
            or self.current_competitiveness != CurrentCompetitiveness.UNKNOWN
            or self.bot_opponent_count is not None
            or self.recent_major_signing
            or self.promotion_objective != DEFAULT_PROMOTION_OBJECTIVE
            or bool(self.league_position)
        )

    @property
    def is_early_season_like(self) -> bool:
        return self.season_phase in (SeasonPhase.PRESEASON, SeasonPhase.EARLY_SEASON)

    @property
    def is_late_season_like(self) -> bool:
        return self.season_phase in (SeasonPhase.LATE_SEASON, SeasonPhase.PROMOTION_STAGE)

    @property
    def promotion_is_urgent(self) -> bool:
        return self.promotion_objective in (
            PromotionObjective.TARGET_THIS_SEASON,
            PromotionObjective.MUST_PROMOTE,
        )

    @property
    def promotion_is_deprioritized(self) -> bool:
        return self.promotion_objective in (
            PromotionObjective.NOT_A_PRIORITY,
            PromotionObjective.WELCOME_IF_NATURAL,
        )

    @property
    def is_dominant_or_strong(self) -> bool:
        return self.current_competitiveness in (
            CurrentCompetitiveness.DOMINANT,
            CurrentCompetitiveness.STRONG,
        )

    def signing_matches_area(self, area: str) -> bool:
        """Whether a recently completed signing plausibly covers
        `area` (e.g. "central_defense", "goalkeeper") -- used to reduce
        urgency for the same structural need, never to erase it (see
        urgency.py)."""
        if not self.recent_major_signing or not self.recent_signing_position:
            return False
        return self.recent_signing_position.upper() in area.upper() or area.upper() in (
            self.recent_signing_position.upper()
        )
