"""Retrospective comparison labeling (Alpha 0.6.6, Part 19).

When only a retrospective PRE exists (no official PRE), the comparison must
be labeled distinctly from a real PRE-vs-POST comparison, with a visible
limitation -- never "PRE oficial vs POST".
"""
from __future__ import annotations

from ht_coach_app.core.localization import t


def comparison_label(has_official_pre, has_retrospective_pre):
    if has_official_pre:
        return t("official_match_intelligence.comparison_label.official")
    if has_retrospective_pre:
        return t("official_match_intelligence.comparison_label.retrospective")
    return t("official_match_intelligence.comparison_label.unavailable")


def retrospective_limitation_text():
    return t("official_match_intelligence.retrospective.limitation")
