from decimal import Decimal

from engine.hattrick_ratings.midfield.models import (
    ContextModifierBreakdown,
    MidfieldRatingContext,
    TeamAttitude,
)


def context_modifiers(context: MidfieldRatingContext):
    parameters = context.model_parameters
    warnings = []
    modifiers = []

    if context.team_spirit is None:
        team_spirit_modifier = Decimal("1.00")
        warnings.append("neutral_team_spirit_assumed")
    else:
        spirit = max(1, min(10, int(context.team_spirit)))
        team_spirit_modifier = Decimal("1.00") + (
            Decimal(spirit - 5) * parameters.team_spirit_step
        )
    modifiers.append(
        ContextModifierBreakdown(
            code="team_spirit",
            modifier=team_spirit_modifier,
            parameters={"team_spirit": context.team_spirit},
        )
    )

    attitude = context.attitude or TeamAttitude.NORMAL
    attitude_key = attitude.value if isinstance(attitude, TeamAttitude) else str(attitude)
    attitude_modifier = parameters.attitude_modifiers.get(attitude_key)
    if attitude_modifier is None:
        attitude_modifier = Decimal("1.00")
        warnings.append("unknown_attitude_assumed_normal")
        attitude_key = TeamAttitude.NORMAL.value
    modifiers.append(
        ContextModifierBreakdown(
            code="attitude",
            modifier=attitude_modifier,
            parameters={"attitude": attitude_key},
        )
    )

    if not context.coach:
        warnings.append("missing_coach_context")

    total = Decimal("1.00")
    for item in modifiers:
        total *= item.modifier
    return total, tuple(modifiers), tuple(warnings)
