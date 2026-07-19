from models.formation import Formation
from models.position import Position


def _formation(name, positions):
    return Formation(
        name=name,
        positions=positions
    )


FORMATION_253 = _formation(
    "2-5-3",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 2,
        Position.WINGER: 2,
        Position.INNER_MIDFIELDER: 3,
        Position.FORWARD: 3,
    }
)


FORMATION_343 = _formation(
    "3-4-3",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 3,
        Position.WINGER: 2,
        Position.INNER_MIDFIELDER: 2,
        Position.FORWARD: 3,
    }
)


FORMATION_352 = _formation(
    "3-5-2",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 3,
        Position.WINGER: 2,
        Position.INNER_MIDFIELDER: 3,
        Position.FORWARD: 2,
    }
)


FORMATION_433 = _formation(
    "4-3-3",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 2,
        Position.WING_BACK: 2,
        Position.INNER_MIDFIELDER: 3,
        Position.FORWARD: 3,
    }
)


FORMATION_442 = _formation(
    "4-4-2",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 2,
        Position.WING_BACK: 2,
        Position.WINGER: 2,
        Position.INNER_MIDFIELDER: 2,
        Position.FORWARD: 2,
    }
)


FORMATION_451 = _formation(
    "4-5-1",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 2,
        Position.WING_BACK: 2,
        Position.WINGER: 2,
        Position.INNER_MIDFIELDER: 3,
        Position.FORWARD: 1,
    }
)


FORMATION_523 = _formation(
    "5-2-3",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 3,
        Position.WING_BACK: 2,
        Position.INNER_MIDFIELDER: 2,
        Position.FORWARD: 3,
    }
)


FORMATION_532 = _formation(
    "5-3-2",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 3,
        Position.WING_BACK: 2,
        Position.INNER_MIDFIELDER: 3,
        Position.FORWARD: 2,
    }
)


FORMATION_541 = _formation(
    "5-4-1",
    {
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 3,
        Position.WING_BACK: 2,
        Position.WINGER: 2,
        Position.INNER_MIDFIELDER: 2,
        Position.FORWARD: 1,
    }
)


FORMATIONS = [
    FORMATION_253,
    FORMATION_343,
    FORMATION_352,
    FORMATION_433,
    FORMATION_442,
    FORMATION_451,
    FORMATION_523,
    FORMATION_532,
    FORMATION_541,
]

FORMATION_BY_NAME = {
    formation.name: formation
    for formation in FORMATIONS
}

DEFAULT_FORMATION_NAMES = [
    "3-5-2",
    "4-5-1",
]


def formation_by_name(name):
    return FORMATION_BY_NAME[name]
