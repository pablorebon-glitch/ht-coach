from __future__ import annotations

from engine.history.enums import ComparisonSelectorType
from engine.history.previous_match_selector import (
    PreviousMatchSelection,
    PreviousMatchSelector,
)

# The previous-match selection architecture (PreviousMatchSelector /
# PreviousMatchSelection / ComparisonSelectorType) already exists from
# the Historical Match Intelligence Foundation sprint. This module is a
# thin, evolution-engine-facing adapter over it — it does not
# re-implement selection logic.

_SELECTOR = PreviousMatchSelector()


def select_previous_match(current, candidates, *, include_planned=False):
    return _SELECTOR.select(
        current,
        candidates,
        PreviousMatchSelection(
            selector_type=ComparisonSelectorType.PREVIOUS_MATCH,
            include_planned=include_planned,
        ),
    )


def select_previous_league_match(current, candidates, *, include_planned=False):
    return _SELECTOR.select(
        current,
        candidates,
        PreviousMatchSelection(
            selector_type=ComparisonSelectorType.PREVIOUS_LEAGUE_MATCH,
            include_planned=include_planned,
        ),
    )


def select_previous_cup_match(current, candidates, *, include_planned=False):
    return _SELECTOR.select(
        current,
        candidates,
        PreviousMatchSelection(
            selector_type=ComparisonSelectorType.PREVIOUS_CUP_MATCH,
            include_planned=include_planned,
        ),
    )


def select_previous_friendly(current, candidates, *, include_planned=False):
    return _SELECTOR.select(
        current,
        candidates,
        PreviousMatchSelection(
            selector_type=ComparisonSelectorType.PREVIOUS_FRIENDLY,
            include_planned=include_planned,
        ),
    )


def select_previous_same_cohort(current, candidates, *, include_planned=False):
    return _SELECTOR.select(
        current,
        candidates,
        PreviousMatchSelection(
            selector_type=ComparisonSelectorType.PREVIOUS_SAME_COHORT,
            include_planned=include_planned,
        ),
    )


def select_custom(
    current,
    candidates,
    *,
    competition_type=None,
    team_type=None,
    same_cohort=False,
    include_planned=False,
):
    return _SELECTOR.select(
        current,
        candidates,
        PreviousMatchSelection(
            selector_type=ComparisonSelectorType.CUSTOM,
            include_planned=include_planned,
            competition_type=competition_type,
            team_type=team_type,
            same_cohort=same_cohort,
        ),
    )
