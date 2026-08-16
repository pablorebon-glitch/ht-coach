from __future__ import annotations

from pathlib import Path

from engine.history.query_service import HistoricalMatchQueryService
from engine.history.serialization import (
    HistoricalSerializationError,
    repository_payload_to_json,
    snapshots_from_repository_payload,
    write_atomic,
)


class HistoricalMatchRepositoryError(ValueError):
    pass


class HistoricalMatchRepository:
    def __init__(self, storage_path):
        self.storage_path = Path(storage_path)
        self._query_service = HistoricalMatchQueryService()

    def save(self, snapshot):
        snapshots = {item.snapshot_id: item for item in self.list_all()}
        snapshots[snapshot.snapshot_id] = snapshot
        self._write(tuple(snapshots.values()))
        return snapshot

    def replace(self, snapshot):
        if self.get(snapshot.snapshot_id) is None:
            raise HistoricalMatchRepositoryError(
                f"historical snapshot not found: {snapshot.snapshot_id}"
            )
        return self.save(snapshot)

    def get(self, snapshot_id):
        for snapshot in self.list_all():
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        return None

    def list_all(self):
        if not self.storage_path.exists():
            return ()
        try:
            return self._query_service.filter(
                snapshots_from_repository_payload(
                    self.storage_path.read_text(encoding="utf-8")
                )
            )
        except HistoricalSerializationError as exc:
            raise HistoricalMatchRepositoryError(str(exc)) from exc

    def delete(self, snapshot_id):
        remaining = tuple(
            snapshot
            for snapshot in self.list_all()
            if snapshot.snapshot_id != snapshot_id
        )
        self._write(remaining)

    def find_by_match_id(self, match_id):
        if not match_id:
            return None
        for snapshot in self.list_all():
            if snapshot.match_context.official_match_id == match_id:
                return snapshot
        return None

    def find_by_provisional_identity(self, provisional_identity):
        """Alpha 0.6.6, Part 11: looks up a record by its provisional
        identity (season + week + date + opponent + competition type)
        -- the only lookup available before a real Match ID exists."""
        if not provisional_identity:
            return None
        for snapshot in self.list_all():
            if snapshot.provisional_identity == provisional_identity:
                return snapshot
        return None

    def query(self, criteria):
        return self._query_service.filter(self.list_all(), criteria)

    def import_snapshots(self, snapshots, replace_existing=False):
        existing = {snapshot.snapshot_id: snapshot for snapshot in self.list_all()}
        imported = 0
        skipped = []
        for snapshot in snapshots:
            if snapshot.snapshot_id in existing and not replace_existing:
                skipped.append(snapshot.snapshot_id)
                continue
            existing[snapshot.snapshot_id] = snapshot
            imported += 1
        self._write(tuple(existing.values()))
        return {"imported": imported, "skipped": tuple(skipped)}

    def _write(self, snapshots):
        ordered = self._query_service.filter(snapshots)
        ids = [snapshot.snapshot_id for snapshot in ordered]
        if len(ids) != len(set(ids)):
            raise HistoricalMatchRepositoryError("duplicate historical snapshot ID")
        write_atomic(self.storage_path, repository_payload_to_json(ordered))
