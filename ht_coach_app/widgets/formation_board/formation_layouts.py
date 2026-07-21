from dataclasses import dataclass

from ht_coach_app.core.position_formatting import (
    format_position,
    normalize_position_key,
)
from ht_coach_app.core.side_formatting import format_side
from models.formations import FORMATIONS
from models.position import Position
from models.side import Side


@dataclass(frozen=True)
class SlotLayout:
    slot_id: str
    line: str
    side: str
    side_label: str
    position: str
    position_label: str
    normalized_x: float
    normalized_y: float


_LINE_Y = {
    "goalkeeper": 0.13,
    "defense": 0.35,
    "midfield": 0.58,
    "forward": 0.82,
}


def supported_formation_layouts():
    return {
        formation.name: get_formation_layout(formation.name)
        for formation in FORMATIONS
    }


def get_formation_layout(formation_name):
    formation = next(
        formation
        for formation in FORMATIONS
        if formation.name == formation_name
    )
    slots = []

    slots.extend(
        _slots(
            formation_name,
            "goalkeeper",
            Position.GOALKEEPER,
            [Side.CENTER],
            [0.50],
        )
    )
    slots.extend(
        _defense_slots(
            formation_name,
            formation.positions
        )
    )
    slots.extend(
        _midfield_slots(
            formation_name,
            formation.positions
        )
    )
    slots.extend(
        _attack_slots(
            formation_name,
            formation.positions
        )
    )

    return tuple(slots)


def _defense_slots(formation_name, positions):
    slots = []
    wing_backs = positions.get(Position.WING_BACK, 0)
    central_defenders = positions.get(Position.CENTRAL_DEFENDER, 0)

    if wing_backs:
        slots.extend(
            _slots(
                formation_name,
                "defense",
                Position.WING_BACK,
                [Side.LEFT, Side.RIGHT],
                [0.10, 0.90],
            )
        )

    if central_defenders:
        sides, xs = _line_distribution(central_defenders)
        slots.extend(
            _slots(
                formation_name,
                "defense",
                Position.CENTRAL_DEFENDER,
                sides,
                xs,
            )
        )

    return sorted(
        slots,
        key=lambda slot: slot.normalized_x
    )


def _midfield_slots(formation_name, positions):
    slots = []
    wingers = positions.get(Position.WINGER, 0)
    inner_midfielders = positions.get(Position.INNER_MIDFIELDER, 0)

    if wingers:
        slots.extend(
            _slots(
                formation_name,
                "midfield",
                Position.WINGER,
                [Side.LEFT, Side.RIGHT],
                [0.10, 0.90],
            )
        )

    if inner_midfielders:
        sides, xs = _line_distribution(inner_midfielders)
        slots.extend(
            _slots(
                formation_name,
                "midfield",
                Position.INNER_MIDFIELDER,
                sides,
                xs,
            )
        )

    return sorted(
        slots,
        key=lambda slot: slot.normalized_x
    )


def _attack_slots(formation_name, positions):
    forwards = positions.get(Position.FORWARD, 0)
    sides, xs = _line_distribution(forwards)
    return _slots(
        formation_name,
        "forward",
        Position.FORWARD,
        sides,
        xs,
    )


def _line_distribution(count):
    if count == 1:
        return [Side.CENTER], [0.50]

    if count == 2:
        return [Side.LEFT, Side.RIGHT], [0.38, 0.62]

    return [Side.LEFT, Side.CENTER, Side.RIGHT], [0.30, 0.50, 0.70]


def _slots(formation_name, line, position, sides, xs):
    return tuple(
        SlotLayout(
            slot_id=(
                f"{formation_name}:{line}:"
                f"{normalize_position_key(position)}:{side.value}:{index + 1}"
            ),
            line=line,
            side=side.value,
            side_label=format_side(side),
            position=normalize_position_key(position),
            position_label=format_position(position),
            normalized_x=xs[index],
            normalized_y=_LINE_Y[line],
        )
        for index, side in enumerate(sides)
    )
