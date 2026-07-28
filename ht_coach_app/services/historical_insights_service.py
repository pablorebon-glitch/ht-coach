from __future__ import annotations

from engine.history.evolution.comparison_engine import HistoricalEvolutionEngine
from engine.history.insights import generate_insights
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.core.paths import historical_match_snapshots_path

_COMPARISON_TARGET_KEYS = {
    "previous": "insight.comparison_target.previous_match",
    "previous_league": "insight.comparison_target.previous_league_match",
    "previous_cup": "insight.comparison_target.previous_cup_match",
    "previous_friendly": "insight.comparison_target.previous_friendly_match",
    "same_cohort": "insight.comparison_target.same_cohort_match",
}


class HistoricalInsightsAppService:
    """App-facing bridge for the Alpha 0.5.8.4 Historical Insights
    Engine. Like its Alpha 0.5.8.3 counterpart, this is not wired into
    any view yet — see HistoricalEvolutionAppService for why. It exists
    so a future Match History screen has one ready entry point that
    already combines snapshot lookup, evolution and insight generation,
    instead of a controller having to orchestrate all three engines
    itself.
    """

    def __init__(self, repository=None, evolution_engine=None):
        self._repository = repository or HistoricalMatchRepository(
            historical_match_snapshots_path()
        )
        self._evolution_engine = evolution_engine or HistoricalEvolutionEngine()

    def compare_with_previous(self, current_snapshot_id, include_planned=False):
        return self._run(
            current_snapshot_id,
            "previous",
            lambda current, candidates: self._evolution_engine.compare_with_previous(
                current, candidates, include_planned=include_planned
            ),
        )

    def compare_with_previous_league(self, current_snapshot_id, include_planned=False):
        return self._run(
            current_snapshot_id,
            "previous_league",
            lambda current, candidates: (
                self._evolution_engine.compare_with_previous_league(
                    current, candidates, include_planned=include_planned
                )
            ),
        )

    def compare_with_previous_cup(self, current_snapshot_id, include_planned=False):
        return self._run(
            current_snapshot_id,
            "previous_cup",
            lambda current, candidates: self._evolution_engine.compare_with_previous_cup(
                current, candidates, include_planned=include_planned
            ),
        )

    def compare_with_previous_friendly(self, current_snapshot_id, include_planned=False):
        return self._run(
            current_snapshot_id,
            "previous_friendly",
            lambda current, candidates: (
                self._evolution_engine.compare_with_previous_friendly(
                    current, candidates, include_planned=include_planned
                )
            ),
        )

    def compare_same_cohort(self, current_snapshot_id, include_planned=False):
        return self._run(
            current_snapshot_id,
            "same_cohort",
            lambda current, candidates: self._evolution_engine.compare_same_cohort(
                current, candidates, include_planned=include_planned
            ),
        )

    def compare_with_custom_snapshot(self, current_snapshot_id, previous_snapshot_id):
        current = self._repository.get(current_snapshot_id)
        previous = self._repository.get(previous_snapshot_id)
        if current is None or previous is None:
            return None
        evolution = self._evolution_engine.compare(current, previous)
        return generate_insights(
            current,
            previous,
            evolution,
            comparison_target_key="insight.comparison_target.custom",
        )

    def _run(self, current_snapshot_id, selector_key, select_and_compare):
        current = self._repository.get(current_snapshot_id)
        if current is None:
            return None
        candidates = [
            snapshot for snapshot in self._repository.list_all()
            if snapshot.snapshot_id != current_snapshot_id
        ]
        evolution = select_and_compare(current, candidates)
        if evolution is None:
            return None
        previous = self._repository.get(evolution.previous_snapshot_id)
        if previous is None:
            return None
        return generate_insights(
            current,
            previous,
            evolution,
            comparison_target_key=_COMPARISON_TARGET_KEYS[selector_key],
        )
