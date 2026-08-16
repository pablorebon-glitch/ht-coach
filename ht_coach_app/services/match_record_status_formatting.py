from __future__ import annotations

from ht_coach_app.core.localization import t


def match_record_status_label(status):
    value = getattr(status, "value", status)
    return t(f"match_record_status.{value}")
