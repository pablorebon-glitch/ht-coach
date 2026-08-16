"""Compares a previously planned lineup against a new recommendation
(Alpha 0.6.6, Part 2). Pure post-processing over already-computed
`FormationAnalysisResult` objects -- never touches the optimizer, never
recomputes a rating or probability.
"""
from __future__ import annotations

from datetime import datetime, timezone

from engine.lineup_memory.models import ChangedSlot, MatchPlanRevision, SectorDelta
from engine.ratings.sector_rating import CANONICAL_SECTORS


def compare_lineups(previous_result, new_result, match_record_id="", source_csv=""):
    """Builds a `MatchPlanRevision` from two `FormationAnalysisResult`s
    (or `previous_result=None` when there was nothing previously
    planned for this match). Compares by starting-XI slot number, so a
    formation change (different slot shapes) is reported as
    `changed_formation` rather than attempting a slot-by-slot diff that
    wouldn't be meaningful across different formations.
    """
    previous_lineup = tuple(getattr(previous_result, "lineup", ()) or ())
    new_lineup = tuple(new_result.lineup)

    changed_formation = bool(previous_result) and (
        previous_result.formation_name != new_result.formation_name
    )
    changed_tactic = bool(previous_result) and (
        previous_result.recommended_tactic != new_result.recommended_tactic
    )

    changed_slots = []
    changed_orders_only = []
    changed_player_names = []

    if previous_result is not None and not changed_formation:
        previous_by_number = {p.number: p for p in previous_lineup}
        new_by_number = {p.number: p for p in new_lineup}

        for number in sorted(set(previous_by_number) & set(new_by_number)):
            prev = previous_by_number[number]
            new = new_by_number[number]
            entry = ChangedSlot(
                number=number,
                position=new.position,
                side=new.side,
                previous_player_name=prev.player_name,
                new_player_name=new.player_name,
                previous_order=prev.order,
                new_order=new.order,
                previous_order_side=prev.order_side,
                new_order_side=new.order_side,
            )
            if not entry.player_changed and not entry.order_changed:
                continue
            changed_slots.append(entry)
            if entry.player_changed:
                if new.player_name:
                    changed_player_names.append(new.player_name)
                if prev.player_name:
                    changed_player_names.append(prev.player_name)
            else:
                changed_orders_only.append(entry)

    sector_deltas = []
    if previous_result is not None:
        for sector in CANONICAL_SECTORS:
            previous_value = getattr(previous_result.team_ratings, sector, None)
            new_value = getattr(new_result.team_ratings, sector, None)
            if previous_value is None or new_value is None:
                continue
            sector_deltas.append(
                SectorDelta(
                    sector=sector,
                    previous_value=previous_value,
                    new_value=new_value,
                    delta=round(new_value - previous_value, 4),
                )
            )

    possession_delta = (
        round(new_result.possession - previous_result.possession, 4)
        if previous_result is not None
        else 0.0
    )
    xg_delta = (
        round(new_result.expected_goals - previous_result.expected_goals, 4)
        if previous_result is not None
        else 0.0
    )
    win_probability_delta = (
        round(new_result.win_probability - previous_result.win_probability, 4)
        if previous_result is not None
        else 0.0
    )

    return MatchPlanRevision(
        match_record_id=match_record_id,
        previous_lineup=previous_lineup,
        new_lineup=new_lineup,
        changed_slots=tuple(changed_slots),
        changed_players=tuple(dict.fromkeys(changed_player_names)),
        changed_orders=tuple(changed_orders_only),
        changed_formation=changed_formation,
        previous_formation=getattr(previous_result, "formation_name", ""),
        new_formation=new_result.formation_name,
        changed_tactic=changed_tactic,
        previous_tactic=getattr(previous_result, "recommended_tactic", ""),
        new_tactic=new_result.recommended_tactic,
        sector_deltas=tuple(sector_deltas),
        possession_delta=possession_delta,
        xg_delta=xg_delta,
        win_probability_delta=win_probability_delta,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_csv=source_csv,
    )
