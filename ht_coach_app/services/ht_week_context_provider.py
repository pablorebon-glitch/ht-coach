"""The single shared `HTCalendarService` instance every app-layer module
reads from (Part 8: "Single provider", Part 10: "Every module asking
'what week is this?' must query HTCalendarService. No direct datetime
arithmetic.").

Weekly Planner, Club Advisor, Match Intelligence, Evolution and History
all import `get_calendar_service()` (or `current_week_snapshot()`
directly) instead of constructing their own `HTCalendarService()` or
touching `datetime.now()`/`date.today()` themselves.
"""
from __future__ import annotations

from engine.calendar import HTCalendarService, HTWeekSnapshot

_shared_service: HTCalendarService | None = None


def get_calendar_service() -> HTCalendarService:
    """The one `HTCalendarService` instance the whole app shares.
    Deliberately module-level (not a Qt singleton) so pure-engine code
    can use it too without any Qt dependency."""
    global _shared_service
    if _shared_service is None:
        _shared_service = HTCalendarService()
    return _shared_service


def set_calendar_service(service: HTCalendarService) -> None:
    """Test/override hook -- lets a test inject a service with a fixed
    clock without needing to patch a module-level global directly."""
    global _shared_service
    _shared_service = service


def current_week_snapshot(now=None) -> HTWeekSnapshot:
    return get_calendar_service().week_snapshot(now)
