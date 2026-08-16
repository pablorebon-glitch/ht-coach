from __future__ import annotations

from ht_coach_app.core.localization import t


def format_ht_week_status(snapshot) -> str:
    """The compact "Current HT Week" header text (Part 9): each of the
    five weekly milestones as a Pending/Processed(-equivalent) pair, on
    one line each -- never a large widget."""
    training_label = t("ht_week.processed" if snapshot.training_processed else "ht_week.pending")
    friendly_label = t("ht_week.played" if snapshot.friendly_played else "ht_week.pending")
    league_label = t("ht_week.played" if snapshot.league_match_played else "ht_week.pending")
    financial_label = t(
        "ht_week.completed" if snapshot.financial_update_completed else "ht_week.pending"
    )
    youth_label = t("ht_week.completed" if snapshot.youth_scout_completed else "ht_week.pending")

    return " | ".join(
        [
            f"{t('ht_week.training')}: {training_label}",
            f"{t('ht_week.friendly')}: {friendly_label}",
            f"{t('ht_week.league')}: {league_label}",
            f"{t('ht_week.financial_update')}: {financial_label}",
            f"{t('ht_week.youth_scout')}: {youth_label}",
        ]
    )
