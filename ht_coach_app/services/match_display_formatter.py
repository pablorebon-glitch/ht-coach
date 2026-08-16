"""Central match display formatter (Alpha 0.6.7 HF-02, Part 6).

One single source of truth for rendering a match's identity, used
everywhere a match needs to be named: Saved Matches, the Official
Intelligence selector, the Match workspace title, Weekly Planner, and
history. Never appends status/PRE/POST/Complete -- that lives in a separate
metadata block wherever the caller needs it. Never produces duplicated
name fragments.
"""
from __future__ import annotations

from engine.history.match_identity import (
    extract_opponent_name_from_match_identity as _extract_opponent_name,
)

DEFAULT_OUR_TEAM_NAME = "Hit'em up"


def format_match_identity(our_team_name, opponent_name, venue_role="unknown"):
    our_team_name = (our_team_name or "").strip()
    opponent_name = (opponent_name or "").strip()
    role = str(getattr(venue_role, "value", venue_role) or "unknown").lower()

    if role == "away":
        left, right = opponent_name, our_team_name
    else:
        left, right = our_team_name, opponent_name

    left = left or "?"
    right = right or "?"
    identity = f"{left} vs. {right}"

    if role == "neutral":
        identity = f"{identity} \u00b7 Neutral"

    return identity


def format_match_selector_option(our_team_name, opponent_name):
    our_team_name = (our_team_name or "").strip()
    opponent_name = (opponent_name or "").strip() or "?"
    if not our_team_name:
        return opponent_name
    return f"{opponent_name} - {our_team_name}"


def extract_display_opponent_name(
    value,
    our_team_name=DEFAULT_OUR_TEAM_NAME,
):
    """Return a canonical opponent name from a displayed match identity.

    Display labels such as "Hit'em up - Santa Cruz Club" or
    "Hit'em up vs. Santa Cruz Club" are presentation strings, not opponent
    identities. This helper is intentionally conservative: it only strips the
    configured own-team name from common two-team display patterns.
    """
    return _extract_opponent_name(value, our_team_name)


def extract_opponent_name_from_match_identity(
    value,
    our_team_name=DEFAULT_OUR_TEAM_NAME,
):
    return extract_display_opponent_name(value, our_team_name)


class MatchDisplayFormatter:
    """Canonical match identity renderer.

    Retrospective evidence is intentionally excluded: its source opponent and
    source Match ID describe the later reconstruction, not the real historical
    match.
    """

    def __init__(self, default_our_team_name=DEFAULT_OUR_TEAM_NAME):
        self.default_our_team_name = default_our_team_name

    def our_team_name_for_record(self, record):
        if record is None:
            return self.default_our_team_name
        if (
            record.official_pre is not None
            and self._looks_like_single_team_name(record.official_pre.team_name)
        ):
            return record.official_pre.team_name
        if (
            record.official_post is not None
            and self._looks_like_single_team_name(record.official_post.team_name)
        ):
            return record.official_post.team_name
        return self.default_our_team_name

    @staticmethod
    def _looks_like_single_team_name(team_name):
        value = (team_name or "").strip()
        return bool(value) and " - " not in value and " vs. " not in value.lower()

    def format_record_identity(self, record):
        if record is None:
            return format_match_identity(self.default_our_team_name, "")
        context = record.match_context
        opponent = context.opponent.opponent_name if context.opponent else ""
        return format_match_identity(
            self.our_team_name_for_record(record),
            opponent,
            context.home_away,
        )


def format_match_record_identity(record, default_our_team_name=DEFAULT_OUR_TEAM_NAME):
    return MatchDisplayFormatter(default_our_team_name).format_record_identity(record)
