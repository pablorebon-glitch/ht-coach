from __future__ import annotations


class SquadIntelligenceError(ValueError):
    pass


def ensure_player_context_valid(player_context):
    if player_context is None:
        raise SquadIntelligenceError("player_context is required")
    if not player_context.player_name:
        raise SquadIntelligenceError("player_context.player_name is required")
