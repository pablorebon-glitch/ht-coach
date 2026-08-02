"""Central match display formatter (Alpha 0.6.7 HF-02, Part 6).

One single source of truth for rendering a match's identity, used
everywhere a match needs to be named: Saved Matches, the Official
Intelligence selector, the Match workspace title, Weekly Planner, and
history. Never appends status/PRE/POST/Complete -- that lives in a separate
metadata block wherever the caller needs it. Never produces duplicated
name fragments.
"""
from __future__ import annotations


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
