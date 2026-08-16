"""Helpers for separating stored opponent identity from display titles."""

from __future__ import annotations


def extract_opponent_name_from_match_identity(value, our_team_name):
    text = (value or "").strip()
    own = (our_team_name or "").strip()
    if not text or not own:
        return text

    lower_own = own.lower()
    for separator in (" vs. ", " - "):
        if separator not in text:
            continue
        parts = [part.strip() for part in text.split(separator) if part.strip()]
        if len(parts) != 2:
            continue
        left, right = parts
        if left.lower() == lower_own and right.lower() != lower_own:
            return right
        if right.lower() == lower_own and left.lower() != lower_own:
            return left

    return text
