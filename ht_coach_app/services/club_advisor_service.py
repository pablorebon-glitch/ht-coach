from __future__ import annotations

from engine.club_advisor import generate_report
from engine.club_advisor.context import ClubAdvisorContext
from engine.squad_intelligence.enums import ClubStrategy


class ClubAdvisorAppService:
    """Bridges the current roster and training context into the Club
    Advisor -- never recomputes a player's role or rating itself; it
    only aggregates Squad Intelligence's already-computed reports."""

    def __init__(self, squad_intelligence_service=None, weekly_training_service=None):
        from ht_coach_app.services.squad_intelligence_service import (
            SquadIntelligenceAppService,
        )
        from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService

        self._weekly_training_service = weekly_training_service or WeeklyTrainingAppService()
        self._squad_intelligence_service = (
            squad_intelligence_service
            or SquadIntelligenceAppService(weekly_training_service=self._weekly_training_service)
        )

    def build_context(self, players) -> ClubAdvisorContext:
        squad_context = self._squad_intelligence_service.build_squad_context(players)
        squad_reports = self._squad_intelligence_service.generate_squad_reports(players)

        return ClubAdvisorContext(
            strategy=ClubStrategy.SUSTAINABLE_GROWTH,
            squad_reports=squad_reports,
            squad_context=squad_context,
            active_training_type=squad_context.active_training_type,
            has_historical_data=False,
        )

    def generate_report(self, players, season_context=None):
        context = self.build_context(players)
        return generate_report(context, season_context=season_context)
