from models.position import Position
from engine.weekly_training.training_definition import TrainingDefinition
from engine.weekly_training.training_effects import TrainingEffect
from engine.weekly_training.training_types import TrainingType

FULL = TrainingEffect.FULL
REDUCED = TrainingEffect.REDUCED
VERY_SMALL = TrainingEffect.VERY_SMALL
NONE_EFFECT = TrainingEffect.NONE

GK = Position.GOALKEEPER
CD = Position.CENTRAL_DEFENDER
WB = Position.WING_BACK
IM = Position.INNER_MIDFIELDER
WG = Position.WINGER
FW = Position.FORWARD


_CATALOG = {
    TrainingType.GENERAL: TrainingDefinition(
        training_type=TrainingType.GENERAL,
        primary_skills=("form", "goalkeeping"),
        position_effects={GK: {"goalkeeping": VERY_SMALL}},
        all_playing_effect={"form": FULL},
        notes_key="training.notes.general",
    ),
    TrainingType.SET_PIECES: TrainingDefinition(
        training_type=TrainingType.SET_PIECES,
        primary_skills=("set_pieces",),
        all_playing_effect={"set_pieces": FULL},
        special_bonus_rules=("goalkeeper_bonus", "set_pieces_taker_bonus"),
        notes_key="training.notes.set_pieces",
    ),
    TrainingType.DEFENDING: TrainingDefinition(
        training_type=TrainingType.DEFENDING,
        primary_skills=("defending",),
        position_effects={
            CD: {"defending": FULL},
            WB: {"defending": FULL},
        },
        all_playing_effect={"defending": VERY_SMALL},
        notes_key="training.notes.defending",
    ),
    TrainingType.SCORING: TrainingDefinition(
        training_type=TrainingType.SCORING,
        primary_skills=("scoring",),
        position_effects={FW: {"scoring": FULL}},
        all_playing_effect={"scoring": VERY_SMALL},
        notes_key="training.notes.scoring",
    ),
    TrainingType.WINGER: TrainingDefinition(
        training_type=TrainingType.WINGER,
        primary_skills=("winger",),
        position_effects={
            WG: {"winger": FULL},
            WB: {"winger": REDUCED},
        },
        all_playing_effect={"winger": VERY_SMALL},
        notes_key="training.notes.winger",
    ),
    TrainingType.SHOOTING: TrainingDefinition(
        training_type=TrainingType.SHOOTING,
        primary_skills=("scoring", "set_pieces"),
        all_playing_effect={"scoring": REDUCED, "set_pieces": VERY_SMALL},
        notes_key="training.notes.shooting",
    ),
    TrainingType.SHORT_PASSES: TrainingDefinition(
        training_type=TrainingType.SHORT_PASSES,
        primary_skills=("passing",),
        position_effects={
            IM: {"passing": FULL},
            WG: {"passing": FULL},
            FW: {"passing": FULL},
        },
        all_playing_effect={"passing": VERY_SMALL},
        notes_key="training.notes.short_passes",
    ),
    TrainingType.PLAYMAKING: TrainingDefinition(
        training_type=TrainingType.PLAYMAKING,
        primary_skills=("playmaking",),
        position_effects={
            IM: {"playmaking": FULL},
            WG: {"playmaking": REDUCED},
        },
        all_playing_effect={"playmaking": VERY_SMALL},
        notes_key="training.notes.playmaking",
    ),
    TrainingType.GOALKEEPING: TrainingDefinition(
        training_type=TrainingType.GOALKEEPING,
        primary_skills=("goalkeeping",),
        position_effects={GK: {"goalkeeping": FULL}},
        notes_key="training.notes.goalkeeping",
    ),
    TrainingType.THROUGH_PASSES: TrainingDefinition(
        training_type=TrainingType.THROUGH_PASSES,
        primary_skills=("passing",),
        position_effects={
            CD: {"passing": FULL},
            WB: {"passing": FULL},
            IM: {"passing": FULL},
            WG: {"passing": FULL},
        },
        all_playing_effect={"passing": VERY_SMALL},
        notes_key="training.notes.through_passes",
    ),
    TrainingType.DEFENSIVE_POSITIONS: TrainingDefinition(
        training_type=TrainingType.DEFENSIVE_POSITIONS,
        primary_skills=("defending",),
        position_effects={
            GK: {"defending": REDUCED},
            CD: {"defending": REDUCED},
            WB: {"defending": REDUCED},
            IM: {"defending": REDUCED},
            WG: {"defending": REDUCED},
        },
        all_playing_effect={"defending": VERY_SMALL},
        notes_key="training.notes.defensive_positions",
    ),
    TrainingType.WING_ATTACKS: TrainingDefinition(
        training_type=TrainingType.WING_ATTACKS,
        primary_skills=("winger",),
        position_effects={
            WG: {"winger": FULL},
            FW: {"winger": FULL},
        },
        all_playing_effect={"winger": VERY_SMALL},
        notes_key="training.notes.wing_attacks",
    ),
}


def definition_for(training_type) -> TrainingDefinition | None:
    """Looks up a TrainingDefinition by TrainingType (or its raw stable
    string value). Returns None for anything unrecognized rather than
    raising, so an unknown/future training type degrades to a safe
    "unsupported" state instead of crashing."""
    parsed = training_type
    if not isinstance(parsed, TrainingType):
        parsed = TrainingType.parse(training_type)
    if parsed is None:
        return None
    return _CATALOG.get(parsed)


def all_definitions():
    """All 12 definitions, in stable TrainingType declaration order."""
    return tuple(_CATALOG[training_type] for training_type in TrainingType)
