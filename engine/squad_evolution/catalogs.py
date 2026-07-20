from engine.squad_evolution.models import (
    HORIZON_CURRENT,
    HORIZON_MEDIUM_TERM,
    HORIZON_SHORT_TERM,
    TRAINING_DEFENDING,
    TRAINING_GOALKEEPING,
    TRAINING_PASSING,
    TRAINING_PLAYMAKING,
    TRAINING_SCORING,
    TRAINING_SET_PIECES,
    TRAINING_UNKNOWN,
    TRAINING_WINGER,
)
from models.position import Position


BROAD_ROLES = (
    "Goalkeeper",
    "Central Defense",
    "Wing Defense",
    "Midfield",
    "Winger",
    "Forward",
    "Multi-role",
    "Unknown",
)

POSITION_TO_ROLE = {
    Position.GOALKEEPER.value: "Goalkeeper",
    Position.CENTRAL_DEFENDER.value: "Central Defense",
    Position.WING_BACK.value: "Wing Defense",
    Position.INNER_MIDFIELDER.value: "Midfield",
    Position.WINGER.value: "Winger",
    Position.FORWARD.value: "Forward",
}

TRAINING_FOCUSES = (
    TRAINING_UNKNOWN,
    TRAINING_PLAYMAKING,
    TRAINING_DEFENDING,
    TRAINING_SCORING,
    TRAINING_WINGER,
    TRAINING_GOALKEEPING,
    TRAINING_PASSING,
    TRAINING_SET_PIECES,
)

PLANNING_HORIZONS = (
    HORIZON_CURRENT,
    HORIZON_SHORT_TERM,
    HORIZON_MEDIUM_TERM,
)

TRAINING_TO_ROLES = {
    TRAINING_PLAYMAKING: ("Midfield",),
    TRAINING_DEFENDING: ("Central Defense", "Wing Defense"),
    TRAINING_SCORING: ("Forward",),
    TRAINING_WINGER: ("Winger", "Wing Defense"),
    TRAINING_GOALKEEPING: ("Goalkeeper",),
    TRAINING_PASSING: ("Midfield", "Winger", "Forward"),
    TRAINING_SET_PIECES: ("Multi-role",),
    TRAINING_UNKNOWN: (),
}


def normalize_horizon(value):
    value = str(value or "").strip()
    if value in PLANNING_HORIZONS:
        return value

    return HORIZON_CURRENT


def normalize_training_focus(value):
    value = str(value or "").strip()
    if value in TRAINING_FOCUSES:
        return value

    return TRAINING_UNKNOWN


def role_for_position(position_value):
    normalized = getattr(position_value, "value", position_value)
    return POSITION_TO_ROLE.get(str(normalized or ""), "Unknown")
