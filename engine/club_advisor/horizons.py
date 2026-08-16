from __future__ import annotations

from engine.club_advisor.enums import ActionType, RecommendationHorizon

_ACTION_TO_DEFAULT_HORIZON = {
    ActionType.ACT_NOW: RecommendationHorizon.THIS_WEEK,
    ActionType.MAINTAIN: RecommendationHorizon.CURRENT_SEASON,
    ActionType.MONITOR: RecommendationHorizon.CURRENT_SEASON,
    ActionType.PREPARE: RecommendationHorizon.NEXT_MATCHES,
    ActionType.REEVALUATE: RecommendationHorizon.NEXT_SEASON,
    ActionType.DEFER: RecommendationHorizon.WHEN_CONDITION_CHANGES,
    ActionType.NO_ACTION: RecommendationHorizon.NO_ACTION_REQUIRED,
}


def default_horizon_for_action(action_type, season_context=None) -> RecommendationHorizon:
    """Every Club Advisor priority must have a horizon. Season context
    can sharpen a generic horizon into a season-specific one -- e.g. a
    MONITOR/REEVALUATE action becomes "review before promotion" when
    promotion is actually being targeted, matching the brief's own
    worked example ("Strengthen defense before promotion")."""
    if season_context is not None and season_context.promotion_is_urgent:
        if action_type in (ActionType.MONITOR, ActionType.REEVALUATE, ActionType.PREPARE):
            return RecommendationHorizon.BEFORE_PROMOTION
    if season_context is not None and season_context.season_phase.value == "promotion_stage":
        if action_type in (ActionType.MONITOR, ActionType.REEVALUATE):
            return RecommendationHorizon.BEFORE_PROMOTION
    return _ACTION_TO_DEFAULT_HORIZON.get(action_type, RecommendationHorizon.CURRENT_SEASON)
