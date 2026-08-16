"""Alpha 0.6.7 HF-03, Part 8: formats `models.team_attitude.TeamAttitude`
into localized display labels.
"""
from __future__ import annotations

from models.team_attitude import TeamAttitude

from ht_coach_app.core.localization import t

_KEY_BY_ATTITUDE = {
    TeamAttitude.NORMAL: "normal",
    TeamAttitude.PLAY_IT_COOL: "play_it_cool",
    TeamAttitude.MATCH_OF_THE_SEASON: "match_of_the_season",
}


def format_team_attitude(attitude):
    if isinstance(attitude, str):
        try:
            attitude = TeamAttitude(attitude)
        except ValueError:
            return attitude or ""
    key = _KEY_BY_ATTITUDE.get(attitude)
    if key is None:
        return getattr(attitude, "value", str(attitude))
    return t(f"match.team_attitude.{key}")


def canonical_team_attitude_choices():
    return [(attitude, format_team_attitude(attitude)) for attitude in TeamAttitude]
