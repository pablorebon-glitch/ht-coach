from enum import Enum


class TrainingType(str, Enum):
    """The 12 senior Hattrick training types. Values are the stable,
    persisted identifiers — never store or compare on localized labels."""

    GENERAL = "GENERAL"
    SET_PIECES = "SET_PIECES"
    DEFENDING = "DEFENDING"
    SCORING = "SCORING"
    WINGER = "WINGER"
    SHOOTING = "SHOOTING"
    SHORT_PASSES = "SHORT_PASSES"
    PLAYMAKING = "PLAYMAKING"
    GOALKEEPING = "GOALKEEPING"
    THROUGH_PASSES = "THROUGH_PASSES"
    DEFENSIVE_POSITIONS = "DEFENSIVE_POSITIONS"
    WING_ATTACKS = "WING_ATTACKS"

    @classmethod
    def parse(cls, value, default=None):
        """Tolerant parsing for persisted/legacy values. Returns
        `default` (not an exception) for anything unrecognized, so a
        future/unknown training type degrades to a safe state instead
        of crashing the Planner."""
        try:
            return cls(str(value or "").strip().upper())
        except ValueError:
            return default


# Migration default: any persisted state saved before this sprint has no
# explicit training type and must resolve to PLAYMAKING, preserving the
# only behavior that existed previously. Never overwrite an explicitly
# saved value with this default.
LEGACY_DEFAULT_TRAINING_TYPE = TrainingType.PLAYMAKING
