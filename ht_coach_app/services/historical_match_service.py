from __future__ import annotations

from engine.history.repository import HistoricalMatchRepository
from engine.history.snapshot_factory import HistoricalSnapshotFactory
from engine.history.validation import ensure_valid_snapshot
from ht_coach_app.core.paths import historical_match_snapshots_path


class HistoricalMatchAppService:
    def __init__(self, repository=None, snapshot_factory=None):
        self._repository = repository or HistoricalMatchRepository(
            historical_match_snapshots_path()
        )
        self._snapshot_factory = snapshot_factory or HistoricalSnapshotFactory()

    def create_snapshot_from_match_analysis(
        self,
        result,
        context=None,
        snapshot_id=None,
        source_application_version="",
        source_engine_version="",
        notes="",
    ):
        snapshot = self._snapshot_factory.from_match_analysis(
            result,
            context=context,
            snapshot_id=snapshot_id,
            source_application_version=source_application_version,
            source_engine_version=source_engine_version,
            notes=notes,
        )
        return ensure_valid_snapshot(
            self._repository.save(snapshot),
            allow_played_without_official=True,
        )
