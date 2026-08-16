"""Alpha 0.6.7 HF-03, Parts 13, 15: a small, in-memory ring buffer of
recent application events.
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger("ht_coach.events")

_MAX_EVENTS = 20


@dataclass(frozen=True)
class AppEvent:
    timestamp: str
    action: str
    match_record_id: str = ""
    outcome: str = "ok"
    detail: str = ""


class EventBuffer:
    def __init__(self, max_events=_MAX_EVENTS):
        self._events = deque(maxlen=max_events)

    def record(self, action, match_record_id="", outcome="ok", detail=""):
        event = AppEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            match_record_id=match_record_id or "",
            outcome=outcome,
            detail=detail,
        )
        self._events.append(event)
        logger.info(
            "action=%s record=%s outcome=%s detail=%s",
            action, event.match_record_id, outcome, detail,
        )
        return event

    def recent(self):
        return tuple(self._events)

    def clear(self):
        self._events.clear()


_global_buffer = EventBuffer()


def record_event(action, match_record_id="", outcome="ok", detail=""):
    return _global_buffer.record(action, match_record_id, outcome, detail)


def recent_events():
    return _global_buffer.recent()


def reset_event_buffer():
    _global_buffer.clear()
