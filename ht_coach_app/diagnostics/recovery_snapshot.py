"""Alpha 0.6.7 HF-03, Part 16: auto-save safety snapshot.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def recovery_snapshot_directory():
    return Path("logs") / "recovery"


class RecoverySnapshotStore:
    def __init__(self, directory=None):
        self._directory = directory or recovery_snapshot_directory()

    def _path_for(self, match_record_id):
        safe_id = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in match_record_id
        )
        return self._directory / f"{safe_id}.json"

    def save(self, match_record_id, tactic="", team_attitude="", formation_name="", lineup_summary=None):
        if not match_record_id:
            return None
        self._directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "match_record_id": match_record_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "tactic": tactic,
            "team_attitude": team_attitude,
            "formation_name": formation_name,
            "lineup_summary": lineup_summary or [],
        }
        path = self._path_for(match_record_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def load(self, match_record_id):
        path = self._path_for(match_record_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def discard(self, match_record_id):
        path = self._path_for(match_record_id)
        if path.exists():
            path.unlink()

    def has_recovery_snapshot(self, match_record_id):
        return self._path_for(match_record_id).exists()
