from decimal import Decimal

from engine.hattrick_ratings.midfield.models import MatchPeriod, MidfieldModelParameters


def stamina_modifier(stamina, period, parameters: MidfieldModelParameters) -> tuple[Decimal, str | None]:
    normalized_period = period.value if isinstance(period, MatchPeriod) else str(period)
    if normalized_period == MatchPeriod.START.value:
        return Decimal("1.00"), None
    if stamina is None:
        return Decimal("0.86"), "missing_stamina_assumed"
    value = max(1, min(9, int(stamina)))
    modifier = Decimal("1.00") - (
        Decimal(parameters.stamina_neutral - value) * parameters.end_stamina_step
    )
    modifier = min(Decimal("1.04"), modifier)
    modifier = max(parameters.minimum_end_stamina_modifier, modifier)
    return modifier, None
