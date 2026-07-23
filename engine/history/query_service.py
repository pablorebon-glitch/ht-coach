from __future__ import annotations

from dataclasses import dataclass

from engine.history.enums import CompetitionType, HomeAway, SnapshotStage, TeamType
from engine.history.models import MatchCohort


@dataclass(frozen=True)
class HistoricalMatchQuery:
    date_from: str = ""
    date_to: str = ""
    competition_type: CompetitionType | str | None = None
    team_type: TeamType | str | None = None
    snapshot_stage: SnapshotStage | str | None = None
    opponent_id: str = ""
    opponent_name: str = ""
    home_away: HomeAway | str | None = None
    season: str = ""
    cohort: MatchCohort | None = None
    has_official_ratings: bool | None = None
    has_predictions: bool | None = None
    descending: bool = False


class HistoricalMatchQueryService:
    def filter(self, snapshots, query: HistoricalMatchQuery | None = None):
        query = query or HistoricalMatchQuery()
        results = [
            snapshot
            for snapshot in snapshots
            if self._matches(snapshot, query)
        ]
        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.match_context.match_date,
                    item.match_context.kickoff_time,
                    item.created_at,
                    item.snapshot_id,
                ),
                reverse=query.descending,
            )
        )

    def _matches(self, snapshot, query):
        context = snapshot.match_context
        if query.date_from and context.match_date < query.date_from:
            return False
        if query.date_to and context.match_date > query.date_to:
            return False
        if query.competition_type is not None and context.competition_type != CompetitionType.parse(query.competition_type):
            return False
        if query.team_type is not None and context.team_type != TeamType.parse(query.team_type):
            return False
        if query.snapshot_stage is not None and context.snapshot_stage != SnapshotStage.parse(query.snapshot_stage):
            return False
        if query.opponent_id and context.opponent.opponent_id != query.opponent_id:
            return False
        if query.opponent_name and query.opponent_name.lower() not in context.opponent.opponent_name.lower():
            return False
        if query.home_away is not None and context.home_away != HomeAway.parse(query.home_away):
            return False
        if query.season and context.season != query.season:
            return False
        if query.cohort is not None and snapshot.cohort != query.cohort:
            return False
        if query.has_official_ratings is not None:
            official = snapshot.official_result.ratings if snapshot.official_result else None
            if bool(official and official.has_any_rating) != query.has_official_ratings:
                return False
        if query.has_predictions is not None:
            predicted = snapshot.predictions.ratings
            has_predictions = bool(predicted and predicted.has_any_rating)
            if has_predictions != query.has_predictions:
                return False
        return True
