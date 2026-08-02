"""Display formatting for the dual-week distinction (Alpha 0.6.6, Part 9).

Never merges the two concepts into one label -- each line is unambiguous
about which week model it's describing.
"""
from __future__ import annotations

from ht_coach_app.core.localization import t


def format_season_week(season_week):
    if not season_week.is_known:
        return t("dual_week.season_unknown")
    return "\n".join(
        [
            t("dual_week.season_label", number=season_week.season_number),
            t("dual_week.season_week_label", week=season_week.season_week),
        ]
    )


def format_training_cycle(training_week_id):
    return t("dual_week.training_cycle_label", cycle_id=f"ht-week-{training_week_id}")


def format_dual_week_summary(season_week, training_week_id):
    return "\n".join(
        [
            format_season_week(season_week),
            format_training_cycle(training_week_id),
        ]
    )
