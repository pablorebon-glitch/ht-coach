from __future__ import annotations

from engine.weekly_training.training_types import TrainingType

TRAINING_TYPE_LABEL_KEYS = {
    TrainingType.GENERAL: "planner.general",
    TrainingType.SET_PIECES: "planner.set_pieces",
    TrainingType.DEFENDING: "planner.defending",
    TrainingType.SCORING: "planner.scoring",
    TrainingType.WINGER: "planner.winger_training",
    TrainingType.SHOOTING: "planner.shooting",
    TrainingType.SHORT_PASSES: "planner.short_passes",
    TrainingType.PLAYMAKING: "planner.playmaking",
    TrainingType.GOALKEEPING: "planner.goalkeeping",
    TrainingType.THROUGH_PASSES: "planner.through_passes",
    TrainingType.DEFENSIVE_POSITIONS: "planner.defensive_positions",
    TrainingType.WING_ATTACKS: "planner.wing_attacks",
}


def training_type_label_key(training_type) -> str:
    """The localization key for a TrainingType (or its stable string
    value). Falls back to the type's own value for anything not in the
    map (shouldn't happen for the 12 canonical types, but keeps this
    safe for an unrecognized future one)."""
    parsed = training_type
    if not isinstance(parsed, TrainingType):
        parsed = TrainingType.parse(training_type)
    if parsed is None:
        return ""
    return TRAINING_TYPE_LABEL_KEYS.get(parsed, "")
