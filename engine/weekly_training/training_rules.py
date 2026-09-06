from decimal import Decimal

from engine.weekly_training.models import (
    PLAYMAKING,
    ExposureConfidence,
    TrainingCapacity,
    TrainingExposure,
    TrainingSlotClass,
)
from engine.weekly_training.training_catalog import definition_for
from engine.weekly_training.training_types import TrainingType
from models.position import Position


class TrainingRuleProvider:
    training_type = ""

    def supports(self, training_type):
        return str(training_type or "").upper() == self.training_type

    def factor_for_position(self, position):
        raise NotImplementedError

    def slot_class_for_position(self, position):
        return slot_class_for_factor(self.factor_for_position(position))

    def exposure_for_entry(self, match_id, entry, source, confidence):
        factor = self.factor_for_position(entry.position)
        minutes = Decimal(str(entry.played_minutes))
        return TrainingExposure(
            player_id=entry.player_id,
            match_id=match_id,
            position_group=str(entry.position),
            played_minutes=minutes,
            training_factor=factor,
            effective_training_minutes=minutes * factor,
            source=source,
            confidence=confidence,
        )

    def capacity_for_formation(self, formation):
        full = 0
        half = 0
        for position, amount in formation.positions.items():
            factor = self.factor_for_position(position)
            if factor == Decimal("1"):
                full += int(amount)
            elif factor == Decimal("0.5"):
                half += int(amount)
        return TrainingCapacity(
            full_slots=full,
            half_slots=half,
            effective_player_equivalents=Decimal(full) + Decimal("0.5") * Decimal(half),
        )


class PlaymakingTrainingRules(TrainingRuleProvider):
    training_type = PLAYMAKING
    _FACTORS = {
        Position.INNER_MIDFIELDER.value: Decimal("1"),
        Position.WINGER.value: Decimal("0.5"),
    }

    def factor_for_position(self, position):
        value = getattr(position, "value", position)
        return self._FACTORS.get(str(value), Decimal("0"))


def _coerce_position(position):
    if isinstance(position, Position):
        return position
    value = getattr(position, "value", position)
    try:
        return Position(str(value))
    except ValueError:
        return None


def slot_class_for_factor(factor):
    factor = Decimal(str(factor))
    if factor == Decimal("1"):
        return TrainingSlotClass.FULL_TRAINING
    if factor == Decimal("0.5"):
        return TrainingSlotClass.HALF_TRAINING
    return TrainingSlotClass.NO_TRAINING


class CatalogTrainingRules(TrainingRuleProvider):
    """Generalized rule provider driven entirely by a declarative
    `TrainingDefinition` (see training_catalog.py) — supports all 12
    senior training types, including multi-skill ones (e.g. Shooting),
    with no `if training_type == ...` branching.

    For backward compatibility with the single-factor
    `TrainingRuleProvider` interface (used by the Match optimizer and
    coverage math), `factor_for_position` / `exposure_for_entry` report
    the *primary* trained skill (the first one declared for that
    training type). A multi-skill training's secondary skill is still
    fully reflected in `factors_for_position` and
    `best_effect_for_position`/`trainable_positions`, which drive
    position eligibility for the optimizer — only the single stored
    coverage-percentage number is scoped to the primary skill. This is
    a documented, intentional simplification; see docs/WEEKLY_TRAINING_PLANNER.md.
    """

    def __init__(self, definition):
        self._definition = definition
        self.training_type = definition.training_type.value

    @property
    def definition(self):
        return self._definition

    @property
    def trained_skills(self):
        return self._definition.primary_skills

    @property
    def primary_skill(self):
        return self._definition.primary_skills[0]

    def factors_for_position(self, position):
        """{skill: Decimal weight} for every trained skill at this
        position."""
        canonical = _coerce_position(position)
        if canonical is None:
            return {skill: Decimal("0") for skill in self._definition.primary_skills}
        effects = self._definition.effects_for_position(canonical)
        return {skill: effect.weight for skill, effect in effects.items()}

    def factor_for_position(self, position):
        canonical = _coerce_position(position)
        if canonical is None:
            return Decimal("0")
        return self._definition.best_effect_for_position(canonical).weight

    def effect_for_position(self, position, skill=None):
        """The TrainingEffect (not just its weight) for a position and
        skill (defaults to the primary skill) — used by explanation
        text, which should never present a raw weight to the user."""
        canonical = _coerce_position(position)
        if canonical is None:
            from engine.weekly_training.training_effects import TrainingEffect

            return TrainingEffect.NONE
        return self._definition.effect_for(canonical, skill or self.primary_skill)

    def trainable_positions(self):
        return self._definition.trainable_positions()


def rule_provider_for(training_type):
    parsed = TrainingType.parse(training_type)
    if parsed is None:
        return None
    if parsed == TrainingType.PLAYMAKING:
        # Unchanged, byte-for-byte identical to every prior release —
        # see test_playmaking_backward_compatibility for proof the
        # catalog-driven equivalent computes the same factors.
        return PlaymakingTrainingRules()
    definition = definition_for(parsed)
    if definition is None:
        return None
    return CatalogTrainingRules(definition)


def assumed_confidence(minutes_known):
    return ExposureConfidence.CONFIRMED if minutes_known else ExposureConfidence.ASSUMED
