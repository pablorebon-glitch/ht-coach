import json
import os
from datetime import datetime, timezone
from pathlib import Path


TRACE_ENV_VAR = "HT_COACH_RUNTIME_TRACE"
_ANNOUNCED_PATHS = set()


class RuntimeIntegrityTracer:
    """Small opt-in JSONL tracer for state-integrity investigations."""

    def __init__(self, path=None, enabled=None):
        self._enabled = (
            bool(enabled)
            if enabled is not None
            else str(os.environ.get(TRACE_ENV_VAR, "")).strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self._path = Path(path) if path is not None else _default_path()
        if self._enabled:
            self._announce_path_once()
            self.emit("TRACE_ENABLED", trace_path=self._resolved_path())

    @property
    def enabled(self):
        return self._enabled

    @property
    def path(self):
        return self._path

    def emit(self, event_name, **payload):
        if not self._enabled:
            return
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_name": str(event_name),
        }
        event.update(_json_safe(payload))
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as file:
                file.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
                file.write("\n")
        except OSError:
            pass

    def _announce_path_once(self):
        resolved = self._resolved_path()
        if resolved in _ANNOUNCED_PATHS:
            return
        _ANNOUNCED_PATHS.add(resolved)
        print(f"Runtime integrity trace enabled: {resolved}")

    def _resolved_path(self):
        try:
            return str(self._path.resolve())
        except OSError:
            return str(self._path)


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if hasattr(value, "value"):
        return _json_safe(value.value)
    return str(value)


def _default_path():
    try:
        from ht_coach_app.core.paths import logs_dir

        return logs_dir() / "runtime_integrity_trace.jsonl"
    except Exception:
        return Path("logs/runtime_integrity_trace.jsonl")
