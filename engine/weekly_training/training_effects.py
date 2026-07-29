from decimal import Decimal
from enum import Enum


class TrainingEffect(str, Enum):
    """How strongly a position/skill combination trains. Ordered from
    strongest to weakest; `NONE` sorts last."""

    FULL = "FULL"
    REDUCED = "REDUCED"
    VERY_SMALL = "VERY_SMALL"
    NONE = "NONE"

    @property
    def sort_order(self):
        return _ORDER[self]

    @property
    def weight(self):
        """A normalized weight used only for internal coverage/capacity
        math — never presented to the user as an official Hattrick
        percentage. The UI must show the plain effect label (Completo /
        Reducido / Muy reducido / No entrena), not this number."""
        return _WEIGHTS[self]


_ORDER = {
    TrainingEffect.FULL: 0,
    TrainingEffect.REDUCED: 1,
    TrainingEffect.VERY_SMALL: 2,
    TrainingEffect.NONE: 3,
}

# Configurable, not official Hattrick percentages. REDUCED matches the
# "half slot" convention the existing Playmaking implementation already
# used (winger = 0.5); VERY_SMALL is deliberately small but non-zero so
# it can still accumulate some coverage over two matches.
_WEIGHTS = {
    TrainingEffect.FULL: Decimal("1"),
    TrainingEffect.REDUCED: Decimal("0.5"),
    TrainingEffect.VERY_SMALL: Decimal("0.1"),
    TrainingEffect.NONE: Decimal("0"),
}


def best_effect(effects):
    """The strongest effect among an iterable of TrainingEffect values,
    defaulting to NONE for an empty input."""
    effects = list(effects)
    if not effects:
        return TrainingEffect.NONE
    return min(effects, key=lambda effect: effect.sort_order)
