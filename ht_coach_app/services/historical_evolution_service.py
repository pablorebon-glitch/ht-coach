from __future__ import annotations

from engine.history.evolution.comparison_engine import HistoricalEvolutionEngine
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.core.paths import historical_match_snapshots_path


class HistoricalEvolutionAppService:
    """App-facing bridge for the Alpha 0.5.8.3 Historical Evolution Engine.

    Not wired into any view yet: the app has no Match History screen to
    attach it to (Alpha 0.5.8.2 built the snapshot foundation but it
    isn't rendered anywhere either). This service exists so a future UI
    — likely built alongside Alpha 0.5.8.4's insights, so both land in
    one coherent screen instead of two half-features — has a ready
    entry point instead of reaching into engine.history.evolution
    directly from a controller.
    """

    def __init__(self, repository=None, engine=None):
        self._repository = repository or HistoricalMatchRepository(
            historical_match_snapshots_path()
        )
        self._engine = engine or HistoricalEvolutionEngine()

    def compare_with_previous(self, current_snapshot_id, include_planned=False):
        return self._compare(
            current_snapshot_id,
            lambda current, candidates: self._engine.compare_with_previous(
                current, candidates, include_planned=include_planned
            ),
        )

    def compare_with_previous_league(self, current_snapshot_id, include_planned=False):
        return self._compare(
            current_snapshot_id,
            lambda current, candidates: self._engine.compare_with_previous_league(
                current, candidates, include_planned=include_planned
            ),
        )

    def compare_with_previous_cup(self, current_snapshot_id, include_planned=False):
        return self._compare(
            current_snapshot_id,
            lambda current, candidates: self._engine.compare_with_previous_cup(
                current, candidates, include_planned=include_planned
            ),
        )

    def compare_with_previous_friendly(self, current_snapshot_id, include_planned=False):
        return self._compare(
            current_snapshot_id,
            lambda current, candidates: self._engine.compare_with_previous_friendly(
                current, candidates, include_planned=include_planned
            ),
        )

    def compare_same_cohort(self, current_snapshot_id, include_planned=False):
        return self._compare(
            current_snapshot_id,
            lambda current, candidates: self._engine.compare_same_cohort(
                current, candidates, include_planned=include_planned
            ),
        )

    def _compare(self, current_snapshot_id, run):
        current = self._repository.get(current_snapshot_id)
        if current is None:
            return None
        candidates = [
            snapshot for snapshot in self._repository.list_all()
            if snapshot.snapshot_id != current_snapshot_id
        ]
        return run(current, candidates)
