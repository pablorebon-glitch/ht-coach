from dataclasses import dataclass, field

from engine.weekly_training.training_effects import TrainingEffect, best_effect
from engine.weekly_training.training_types import TrainingType


@dataclass(frozen=True)
class TrainingDefinition:
    """A fully declarative description of one training type. Nothing
    that consumes this should need an `if training_type == ...` branch
    — every position/skill combination is looked up here instead."""

    training_type: TrainingType
    primary_skills: tuple[str, ...]
    position_effects: dict = field(default_factory=dict)
    all_playing_effect: dict = field(default_factory=dict)
    special_bonus_rules: tuple[str, ...] = ()
    notes_key: str = ""

    def __post_init__(self):
        if not self.primary_skills:
            raise ValueError(
                f"TrainingDefinition for {self.training_type} needs at least "
                "one primary skill"
            )

    def effect_for(self, position, skill) -> TrainingEffect:
        """The effect a player in `position` receives for `skill`: the
        stronger of any position-specific rule and the training's
        blanket "every participant" effect for that skill."""
        position_effect = self.position_effects.get(position, {}).get(
            skill, TrainingEffect.NONE
        )
        blanket_effect = self.all_playing_effect.get(skill, TrainingEffect.NONE)
        return best_effect([position_effect, blanket_effect])

    def effects_for_position(self, position) -> dict:
        """{skill: TrainingEffect} for every trained skill, at this
        position."""
        return {
            skill: self.effect_for(position, skill) for skill in self.primary_skills
        }

    def best_effect_for_position(self, position) -> TrainingEffect:
        """The strongest effect across all trained skills at this
        position — used where a single effect-level summary is needed
        (e.g. locking a "trainable" slot for the Match optimizer)."""
        return best_effect(self.effects_for_position(position).values())

    def trainable_positions(self):
        """Positions with at least one skill above NONE, ordered
        strongest-effect-first then by position value for determinism."""
        positions = set(self.position_effects.keys())
        if self.all_playing_effect:
            # a blanket effect makes every canonical position eligible,
            # even ones with no specific override
            from models.position import Position

            positions |= set(Position)
        scored = [
            (position, self.best_effect_for_position(position))
            for position in positions
        ]
        scored = [item for item in scored if item[1] != TrainingEffect.NONE]
        scored.sort(key=lambda item: (item[1].sort_order, item[0].value))
        return tuple(position for position, _effect in scored)
