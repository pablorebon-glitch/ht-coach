from decimal import Decimal

from engine.weekly_training.models import (
    CoverageStatus,
    MatchStatus,
    PlayerCoverage,
    TrainingPriority,
)
from engine.weekly_training.player_identity import player_training_id


TARGET_MINUTES = {
    TrainingPriority.REQUIRED_100: Decimal("90"),
    TrainingPriority.REQUIRED_50: Decimal("45"),
    TrainingPriority.HIGH_PRIORITY: Decimal("45"),
    TrainingPriority.SECONDARY_PRIORITY: Decimal("45"),
}


class WeeklyTrainingCoverageService:
    def __init__(self, rule_provider):
        self._rules = rule_provider

    def aggregate(self, players, priorities, match_records):
        confirmed = {}
        assumed = {}
        planned = {}
        sources = {}

        for record in match_records:
            for exposure in record.training_exposure_entries:
                bucket = planned
                if record.planned_or_played == MatchStatus.PLAYED:
                    bucket = confirmed if record.minutes_known else assumed
                bucket[exposure.player_id] = (
                    bucket.get(exposure.player_id, Decimal("0"))
                    + exposure.effective_training_minutes
                )
                sources.setdefault(exposure.player_id, set()).add(record.match_id)

        rows = []
        for player in players:
            player_id = player_training_id(player)
            priority = priorities.get(player_id, TrainingPriority.NO_PRIORITY)
            confirmed_minutes = confirmed.get(player_id, Decimal("0"))
            assumed_minutes = assumed.get(player_id, Decimal("0"))
            planned_minutes = planned.get(player_id, Decimal("0"))
            total_counted = confirmed_minutes + assumed_minutes + planned_minutes
            target = TARGET_MINUTES.get(priority, Decimal("0"))
            remaining = max(Decimal("0"), target - total_counted)
            rows.append(
                PlayerCoverage(
                    player_id=player_id,
                    player_name=player.name,
                    weekly_target=priority,
                    confirmed_exposure=self._percent(confirmed_minutes),
                    assumed_exposure=self._percent(assumed_minutes),
                    planned_exposure=self._percent(planned_minutes),
                    remaining_exposure=self._percent(remaining),
                    target_status=self._status(priority, total_counted, target),
                    source_matches=tuple(sorted(sources.get(player_id, ()))),
                )
            )
        return tuple(rows)

    @staticmethod
    def _percent(minutes):
        return (Decimal(minutes) / Decimal("90")) * Decimal("100")

    @staticmethod
    def _status(priority, total_minutes, target):
        if priority == TrainingPriority.REST:
            return CoverageStatus.UNKNOWN
        if target <= 0:
            return CoverageStatus.UNKNOWN
        if total_minutes <= 0:
            return CoverageStatus.NOT_STARTED
        if total_minutes == target:
            return CoverageStatus.TARGET_MET
        if total_minutes > target:
            return CoverageStatus.TARGET_EXCEEDED
        return CoverageStatus.PARTIALLY_COVERED
