from __future__ import annotations

from decimal import Decimal

from engine.weekly_training.training_rules import rule_provider_for
from models.position import Position

FULL_FACTOR = Decimal("1")
PARTIAL_FACTOR = Decimal("0.5")


def training_position_tiers(training_type):
    """{"full": (position values...), "partial": (position values...)}
    derived entirely from the active training's rule provider -- never a
    hardcoded position list. "Full" is any position at the maximum
    factor (1); "partial" is any position at exactly the catalog's
    REDUCED factor (0.5). The catalog's VERY_SMALL tier (0.1, a blanket
    "every participant gets a token bonus" effect many training types
    apply team-wide) is deliberately excluded from both tiers -- it's
    too negligible to justify its own wizard step. A training type with
    no REDUCED-tier positions at all (e.g. Goalkeeping, or Defending
    once its blanket VERY_SMALL bonus is excluded) yields an empty
    "partial" tuple, which is what lets the wizard skip that step
    automatically."""
    rules = rule_provider_for(training_type)
    if rules is None:
        return {"full": (), "partial": ()}

    full = []
    partial = []
    for position in Position:
        factor = rules.factor_for_position(position)
        if factor is None:
            continue
        if factor >= FULL_FACTOR:
            full.append(position.value)
        elif factor == PARTIAL_FACTOR:
            partial.append(position.value)
    return {"full": tuple(full), "partial": tuple(partial)}


def required_wizard_counts(training_type, positional_depth):
    """How many current-roster players occupy full-tier and partial-tier
    positions respectively, for the given training type. Both the tiers
    (from the catalog) and the counts (from the current roster's
    positional depth) are derived, never hardcoded -- e.g. Playmaking
    yields {"full": 6, "partial": 4} only because that's how many
    players in *this* roster currently have a best position in each
    tier, not a fixed constant."""
    tiers = training_position_tiers(training_type)
    full_count = sum(positional_depth.get(position, 0) for position in tiers["full"])
    partial_count = sum(positional_depth.get(position, 0) for position in tiers["partial"])
    return {"full": full_count, "partial": partial_count}
