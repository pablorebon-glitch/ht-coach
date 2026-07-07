from models.formation import Formation
from models.position import Position


FORMATION_352 = Formation(
    name="3-5-2",
    positions={
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 3,
        Position.WINGER: 2,
        Position.INNER_MIDFIELDER: 3,
        Position.FORWARD: 2,
    }
)


FORMATION_451 = Formation(
    name="4-5-1",
    positions={
        Position.GOALKEEPER: 1,
        Position.CENTRAL_DEFENDER: 2,
        Position.WING_BACK: 2,
        Position.WINGER: 2,
        Position.INNER_MIDFIELDER: 3,
        Position.FORWARD: 1,
    }
)

FORMATIONS = [
    FORMATION_352,
    FORMATION_451,
]