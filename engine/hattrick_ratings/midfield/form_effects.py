from decimal import Decimal

from engine.hattrick_ratings.midfield.models import MidfieldModelParameters


def form_modifier(form, parameters: MidfieldModelParameters) -> tuple[Decimal, str | None]:
    if form is None:
        return Decimal("0.94"), "missing_form_assumed"
    value = max(1, min(8, int(form)))
    modifier = Decimal("1.00") + (
        Decimal(value - parameters.form_neutral) * parameters.form_step
    )
    modifier = max(parameters.minimum_form_modifier, modifier)
    modifier = min(parameters.maximum_form_modifier, modifier)
    return modifier, None
