from __future__ import annotations

from engine.club_advisor.enums import DepthStatus, StrategicNeed

_DEPTH_STATUS_TO_NEED = {
    DepthStatus.NO_REPLACEMENT.value: StrategicNeed.HIGH,
    DepthStatus.FUTURE_SHORTAGE.value: StrategicNeed.HIGH,
    DepthStatus.ONE_REPLACEMENT.value: StrategicNeed.MEDIUM,
    DepthStatus.HEALTHY_COMPETITION.value: StrategicNeed.LOW,
    DepthStatus.EXCESS_PLAYERS.value: StrategicNeed.NONE,
}

_TRAINING_UTILIZATION_HIGH_RATIO = 0.5
_TRAINING_UTILIZATION_MEDIUM_RATIO = 0.3
_VETERAN_SUCCESSION_RATIO = 0.25


def derive_positional_need(depth_summary, *position_values) -> StrategicNeed:
    """The strategic need for one or more positions sharing an "area"
    (e.g. central defense = CENTRAL_DEFENDER + WING_BACK), read directly
    from the depth summary Club Advisor's existing engine already
    computed -- never a recalculation."""
    entries = [
        item for item in depth_summary.positions if item.position in position_values
    ]
    if not entries:
        return StrategicNeed.INSUFFICIENT_DATA
    needs = [
        _DEPTH_STATUS_TO_NEED.get(entry.status, StrategicNeed.INSUFFICIENT_DATA)
        for entry in entries
    ]
    order = [
        StrategicNeed.NONE, StrategicNeed.LOW, StrategicNeed.MEDIUM,
        StrategicNeed.HIGH, StrategicNeed.CRITICAL,
    ]
    ranked = [need for need in needs if need in order]
    if not ranked:
        return StrategicNeed.INSUFFICIENT_DATA
    return max(ranked, key=order.index)


def has_no_replacement(depth_summary, *position_values) -> bool:
    return any(
        item.position in position_values and item.status == DepthStatus.NO_REPLACEMENT.value
        for item in depth_summary.positions
    )


def derive_training_utilization_need(training_summary) -> StrategicNeed:
    total = training_summary.total_players_evaluated
    if not total:
        return StrategicNeed.INSUFFICIENT_DATA
    ratio = training_summary.players_without_training / total
    if ratio >= _TRAINING_UTILIZATION_HIGH_RATIO:
        return StrategicNeed.HIGH
    if ratio >= _TRAINING_UTILIZATION_MEDIUM_RATIO:
        return StrategicNeed.MEDIUM
    if ratio > 0:
        return StrategicNeed.LOW
    return StrategicNeed.NONE


def derive_veteran_succession_need(squad_summary, roster_size) -> StrategicNeed:
    if not roster_size:
        return StrategicNeed.INSUFFICIENT_DATA
    if not squad_summary.veteran_count:
        return StrategicNeed.NONE
    ratio = squad_summary.veteran_count / roster_size
    if ratio >= _VETERAN_SUCCESSION_RATIO:
        return StrategicNeed.MEDIUM
    return StrategicNeed.LOW
