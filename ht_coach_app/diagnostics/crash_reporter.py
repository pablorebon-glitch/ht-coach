"""Alpha 0.6.7 HF-03, Part 13: crash diagnostics.
"""
from __future__ import annotations

import platform
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from ht_coach_app.core.constants import APP_VERSION
from ht_coach_app.diagnostics.app_context import current_context
from ht_coach_app.diagnostics.event_buffer import recent_events


def crash_log_directory():
    return Path("logs") / "crashes"


def write_crash_report(exc_type, exc_value, exc_traceback, directory=None):
    directory = directory or crash_log_directory()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = directory / f"crash_{timestamp}.log"

    try:
        directory.mkdir(parents=True, exist_ok=True)
        context = current_context()
        lines = [
            f"timestamp: {datetime.now(timezone.utc).isoformat()}",
            f"app_version: {APP_VERSION}",
            f"python_version: {sys.version}",
            f"platform: {platform.platform()}",
            "",
            f"active_page: {context.active_page}",
            f"active_match_record_id: {context.active_match_record_id}",
            f"opponent: {context.opponent_name}",
            f"official_match_id: {context.official_match_id}",
            f"current_action: {context.current_action}",
            f"source_csv: {context.source_csv}",
            f"workspace_dirty: {context.workspace_dirty}",
            "",
            "traceback:",
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            "",
            "last_20_events:",
        ]
        for event in recent_events():
            lines.append(
                f"  {event.timestamp} action={event.action} "
                f"record={event.match_record_id} outcome={event.outcome} "
                f"detail={event.detail}"
            )
        log_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        print(f"HT Coach: failed to write crash log to {log_path}", file=sys.stderr)
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    return log_path


def install_crash_handler(on_crash=None):
    previous_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_traceback):
        log_path = write_crash_report(exc_type, exc_value, exc_traceback)
        if on_crash is not None:
            try:
                on_crash(log_path, exc_type, exc_value, exc_traceback)
            except Exception:
                pass
        previous_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _hook
    return previous_hook
