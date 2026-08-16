from __future__ import annotations

from engine.club_advisor.enums import ActionType, OperationalUrgency, StrategicNeed

_TRACKABLE_NEED_TIERS = (StrategicNeed.CRITICAL, StrategicNeed.HIGH, StrategicNeed.MEDIUM)


def determine_action_type(strategic_need, operational_urgency) -> ActionType:
    """The only place strategic need and operational urgency are
    combined into a single recommended action -- always both
    dimensions together, never either alone. See
    docs/CLUB_ADVISOR.md's worked example: HIGH need + LOW urgency ->
    MONITOR, not ACT_NOW and not NO_ACTION."""
    if operational_urgency == OperationalUrgency.INSUFFICIENT_DATA:
        return ActionType.MONITOR

    if operational_urgency == OperationalUrgency.IMMEDIATE:
        return ActionType.ACT_NOW

    if operational_urgency == OperationalUrgency.HIGH:
        if strategic_need == StrategicNeed.CRITICAL:
            return ActionType.ACT_NOW
        return ActionType.PREPARE

    if operational_urgency == OperationalUrgency.MEDIUM:
        return ActionType.MONITOR if strategic_need in _TRACKABLE_NEED_TIERS else ActionType.MAINTAIN

    if operational_urgency == OperationalUrgency.LOW:
        return ActionType.MONITOR if strategic_need in _TRACKABLE_NEED_TIERS else ActionType.MAINTAIN

    if operational_urgency == OperationalUrgency.DEFERRED:
        return ActionType.DEFER if strategic_need in _TRACKABLE_NEED_TIERS else ActionType.NO_ACTION

    if operational_urgency == OperationalUrgency.NONE:
        return ActionType.NO_ACTION

    return ActionType.MONITOR
