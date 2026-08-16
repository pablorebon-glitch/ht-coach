"""Source-selection policy for "our" sector ratings used in Match
Intelligence and opponent calibration (HF-02.2).

Root cause this fixes: `MatchWorkspaceService._map_sector_comparisons`
always hardcoded `our_scale=SOURCE_HT_COACH_INTERNAL`, regardless of
whether an Official PRE Hattrick capture existed for the match being
analyzed. Since the comparison is only ever marked `comparable` when
`our_scale == opponent_scale`, and opponent ratings are frequently
detected as Hattrick-decimal scale, "our" side was *always* excluded
from direct numeric comparison -- even when the manager had already
imported their own Official PRE summary, which is on that exact same
scale.

This module does not touch the lineup optimizer, the tactic optimizer,
or any rating formula. It only decides *which already-computed rating
values* feed into the comparison/tactical-intelligence layer, following
one explicit priority order:

    1. Official PRE (Hattrick's own scale) -- if present for the match.
    2. A calibrated internal estimate -- only once genuinely confirmed
       comparable (not yet the case; see
       `official_rating_formatting.SCALES_CONFIRMED_COMPATIBLE`, still
       False as of this sprint). This tier exists so a future sprint
       can activate it without touching call sites, but it never fires
       today.
    3. The internal diagnostic estimate, with a clear "not directly
       comparable" limitation -- the existing fallback behavior.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.ratings.sector_rating import SOURCE_HATTRICK_DECIMAL, SOURCE_HT_COACH_INTERNAL

SOURCE_OFFICIAL_PRE = "official_pre"
SOURCE_CALIBRATED_INTERNAL = "calibrated_internal"
SOURCE_INTERNAL_DIAGNOSTIC = "internal_diagnostic"

CALIBRATED_INTERNAL_CONFIRMED = False


@dataclass(frozen=True)
class RatingSourceSelection:
    ratings: object
    scale: str
    source: str

    @property
    def is_official(self) -> bool:
        return self.source == SOURCE_OFFICIAL_PRE


def select_our_ratings(internal_team_ratings, official_pre_ratings=None):
    """Returns a `RatingSourceSelection` for "our" side of the sector
    comparison, following the priority order documented above. Never
    mutates either input; `internal_team_ratings` is always still
    available on the result even when Official PRE wins, for secondary
    diagnostics."""
    if official_pre_ratings is not None and _has_any_sector(official_pre_ratings):
        return RatingSourceSelection(
            ratings=official_pre_ratings,
            scale=SOURCE_HATTRICK_DECIMAL,
            source=SOURCE_OFFICIAL_PRE,
        )
    if CALIBRATED_INTERNAL_CONFIRMED:
        return RatingSourceSelection(
            ratings=internal_team_ratings,
            scale=SOURCE_HATTRICK_DECIMAL,
            source=SOURCE_CALIBRATED_INTERNAL,
        )
    return RatingSourceSelection(
        ratings=internal_team_ratings,
        scale=SOURCE_HT_COACH_INTERNAL,
        source=SOURCE_INTERNAL_DIAGNOSTIC,
    )


_CANONICAL_SECTORS = (
    "left_defense", "central_defense", "right_defense", "midfield",
    "left_attack", "central_attack", "right_attack",
)


def _has_any_sector(ratings):
    return any(getattr(ratings, sector, None) is not None for sector in _CANONICAL_SECTORS)
