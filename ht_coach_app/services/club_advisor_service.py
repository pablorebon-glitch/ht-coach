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
        from engine.analyzers.player_analyzer import PlayerAnalyzer

        squad_context = self._squad_intelligence_service.build_squad_context(players)
        squad_reports = self._squad_intelligence_service.generate_squad_reports(players)

        players_by_position: dict[str, list[str]] = {}
        for player in players:
            best_position, _score = PlayerAnalyzer.best_position(player)
            if not best_position:
                continue
            players_by_position.setdefault(best_position, []).append(player.name)

        state = self._weekly_training_service.load_state()
        cycle_id = state.active_week.week_id if state.active_week is not None else ""

        return ClubAdvisorContext(
            strategy=ClubStrategy.SUSTAINABLE_GROWTH,
            squad_reports=squad_reports,
            squad_context=squad_context,
            active_training_type=squad_context.active_training_type,
            coverage_rows=self._weekly_training_service.coverage(players, cycle_id),
            training_priority_rows=self._weekly_training_service.priority_rows(players),
            has_historical_data=False,
            players_by_position={
                position: tuple(names) for position, names in players_by_position.items()
            },
        )

    def generate_report(self, players, season_context=None):
        context = self.build_context(players)
        return generate_report(context, season_context=season_context)
