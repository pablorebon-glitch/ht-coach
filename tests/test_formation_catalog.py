from models.formations import (
    DEFAULT_FORMATION_NAMES,
    FORMATION_BY_NAME,
    FORMATIONS,
)
from models.position import Position


TARGET_FORMATIONS = [
    "2-5-3",
    "3-4-3",
    "3-5-2",
    "4-3-3",
    "4-4-2",
    "4-5-1",
    "5-2-3",
    "5-3-2",
    "5-4-1",
]

VALID_POSITIONS = {
    Position.GOALKEEPER,
    Position.CENTRAL_DEFENDER,
    Position.WING_BACK,
    Position.INNER_MIDFIELDER,
    Position.WINGER,
    Position.FORWARD,
}


def test_complete_formation_catalog_order():
    assert [
        formation.name
        for formation in FORMATIONS
    ] == TARGET_FORMATIONS


def test_catalog_has_no_duplicate_formations():
    names = [
        formation.name
        for formation in FORMATIONS
    ]

    assert len(names) == len(set(names))
    assert set(FORMATION_BY_NAME) == set(names)


def test_every_formation_has_exactly_eleven_slots():
    for formation in FORMATIONS:
        assert sum(formation.positions.values()) == 11


def test_every_formation_uses_supported_positions():
    for formation in FORMATIONS:
        assert set(formation.positions).issubset(
            VALID_POSITIONS
        )
        assert formation.positions[Position.GOALKEEPER] == 1


def test_default_formations_preserve_alpha_scope():
    assert DEFAULT_FORMATION_NAMES == [
        "3-5-2",
        "4-5-1",
    ]
