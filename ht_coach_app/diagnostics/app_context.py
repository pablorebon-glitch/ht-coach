"""Alpha 0.6.7 HF-03, Part 13: a small, global snapshot of "what is the
application currently doing" -- read by the crash reporter when an
unhandled exception happens.
"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class AppContext:
    active_page: str = ""
    active_match_record_id: str = ""
    opponent_name: str = ""
    official_match_id: str = ""
    current_action: str = ""
    source_csv: str = ""
    workspace_dirty: bool = False


_current = AppContext()


def update_context(**changes):
    global _current
    _current = replace(_current, **changes)
    return _current


def current_context():
    return _current


def reset_context():
    global _current
    _current = AppContext()
