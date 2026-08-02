"""Lineup/tactic summary mapper (Alpha 0.6.7, Part 8's remaining piece).

Converts a `FormationAnalysisResult` (the workspace's own optimizer output)
into the canonical record's own `HistoricalLineupEntry`/`TacticalSetup`
summary -- never the full interactive board state (that stays in
`MatchWorkspaceRepository.load_last_result()`, a separate, already-working
mechanism), just enough for a later Edit to show what was actually planned.
"""
from __future__ import annotations

from engine.history.models import HistoricalLineupEntry, TacticalSetup


def build_historical_lineup(formation):
    return tuple(
        HistoricalLineupEntry(
            player_name=player.player_name,
            number=player.number,
            position=player.position,
            side=player.side,
            individual_order=player.order,
            order_side=player.order_side,
        )
        for player in getattr(formation, "lineup", ()) or ()
    )


def build_tactical_setup(formation):
    return TacticalSetup(
        formation=getattr(formation, "formation_name", "") or "",
        selected_tactic=getattr(formation, "recommended_tactic", "") or "",
        tactic_level=getattr(formation, "tactic_level", None),
    )
